"""
Text-based Knowledge Graph Extraction Pipeline

This module implements a pipeline for extracting structured knowledge graphs from text documents.
It processes documents by pages, uses LLM to extract entities and relations, and performs deduplication.

Pipeline Flow:
1. Load document -> 2. Group by page -> 3. Extract entities/relations -> 4. Deduplicate -> 5. Build graph

Author: AI Assistant
Date: 2025-11-10
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from difflib import SequenceMatcher
import dotenv

dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================

class EntityAttribute(BaseModel):
    """Entity attribute definition"""
    name: str = Field(description="Attribute name")
    value: str = Field(description="Attribute value")
    

class Entity(BaseModel):
    """Entity extracted from text"""
    name: str = Field(description="Entity name, should be concise and precise")
    type: str = Field(description="Entity type: company, person, product, technology, organization, location, concept, etc.")
    description: Optional[str] = Field(default=None, description="Brief description of the entity")
    attributes: List[EntityAttribute] = Field(default_factory=list, description="List of entity attributes")
    

class Relation(BaseModel):
    """Relation between two entities"""
    source_entity: str = Field(description="Source entity name")
    target_entity: str = Field(description="Target entity name")
    relation_type: str = Field(description="Relation type: founded_by, invested_by, works_at, located_in, provides, part_of, etc.")
    description: Optional[str] = Field(default=None, description="Description of the relation")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score of the relation")


class ChunkAnalysisResult(BaseModel):
    """Result of analyzing a single chunk"""
    chunk_idx: int = Field(description="Chunk index")
    page_range: str = Field(description="Page range covered by this chunk")
    entities: List[Entity] = Field(default_factory=list, description="Entities extracted from this chunk")
    relations: List[Relation] = Field(default_factory=list, description="Relations extracted from this chunk")
    

class DocumentAnalysisSchema(BaseModel):
    """Complete document analysis result schema for LLM structured output"""
    entities: List[Entity] = Field(default_factory=list, description="List of entities found in the text")
    relations: List[Relation] = Field(default_factory=list, description="List of relations between entities")
    

# =============================================================================
# ONTOLOGY ALIGNMENT SCHEMAS
# =============================================================================

class CoreEntityType:
    """Core entity types based on ontology"""
    COMPANY = "Company"
    PERSON = "Person"
    TECHNOLOGY = "Technology"
    PRODUCT = "Product"
    TAG_CONCEPT = "TagConcept"
    EVENT = "Event"
    SIGNAL = "Signal"
    OTHER = "Other"  # Fallback for unmapped entities
    
    @classmethod
    def all_types(cls):
        return [cls.COMPANY, cls.PERSON, cls.TECHNOLOGY, cls.PRODUCT, cls.TAG_CONCEPT, cls.EVENT, cls.SIGNAL, cls.OTHER]


class CoreRelationType:
    """Core relation types based on ontology"""
    # Company relations
    FOUNDED_BY = "founded_by"              # Company -> Person
    INVESTED_BY = "invested_by"            # Company -> Company/Person
    USES_TECHNOLOGY = "uses_technology"    # Company -> Technology
    IN_SEGMENT = "in_segment"              # Company -> TagConcept
    COMPETES_WITH = "competes_with"        # Company -> Company
    PARTNERS_WITH = "partners_with"        # Company -> Company
    
    # Person relations
    WORKS_AT = "works_at"                  # Person -> Company
    RESEARCHES = "researches"              # Person -> Technology
    EDUCATED_AT = "educated_at"            # Person -> Organization
    
    # Technology relations
    PART_OF = "part_of"                    # Technology -> Technology (hierarchy)
    RELATED_TO = "related_to"              # Technology -> Technology
    APPLIED_IN = "applied_in"              # Technology -> TagConcept
    
    # Event relations
    INVOLVES = "involves"                  # Event -> Company/Person/Technology
    TRIGGERED_BY = "triggered_by"          # Event -> Event
    
    # Generic
    LOCATED_IN = "located_in"              # Any -> Location
    OTHER = "other"                        # Fallback
    
    @classmethod
    def all_types(cls):
        return [
            cls.FOUNDED_BY, cls.INVESTED_BY, cls.USES_TECHNOLOGY, cls.IN_SEGMENT,
            cls.COMPETES_WITH, cls.PARTNERS_WITH, cls.WORKS_AT, cls.RESEARCHES,
            cls.EDUCATED_AT, cls.PART_OF, cls.RELATED_TO, cls.APPLIED_IN,
            cls.INVOLVES, cls.TRIGGERED_BY, cls.LOCATED_IN, cls.OTHER
        ]


class AlignedEntity(BaseModel):
    """Entity aligned to core ontology with structured fields"""
    name: str = Field(description="Canonical name (used as identifier)")
    core_type: str = Field(description="Core entity type from ontology")
    alt_names: List[str] = Field(default_factory=list, description="Alternative names")
    description: Optional[str] = Field(default=None, description="Description")
    
    # Company fields
    legal_name: Optional[str] = Field(default=None, description="Legal company name")
    founded_date: Optional[str] = Field(default=None, description="Founding date")
    stage: Optional[str] = Field(default=None, description="Development stage")
    industry: Optional[str] = Field(default=None, description="Industry sector")
    location: Optional[str] = Field(default=None, description="Location/Region")
    website: Optional[str] = Field(default=None, description="Website URL")
    
    # Person fields
    education: List[str] = Field(default_factory=list, description="Education background")
    positions: List[str] = Field(default_factory=list, description="Work positions")
    expertise: List[str] = Field(default_factory=list, description="Areas of expertise")
    
    # Technology/Product fields
    application_domain: Optional[str] = Field(default=None, description="Application domain")
    technical_characteristics: List[str] = Field(default_factory=list, description="Technical features")
    maturity_level: Optional[str] = Field(default=None, description="Maturity level")
    
    # Product specific
    version: Optional[str] = Field(default=None, description="Product version")
    features: List[str] = Field(default_factory=list, description="Product features")
    
    # Metadata
    source_entities: List[str] = Field(default_factory=list, description="Original entity names")
    confidence: float = Field(default=1.0, description="Alignment confidence")
    provenance: List[str] = Field(default_factory=list, description="Evidence sources")


class AlignedRelation(BaseModel):
    """Relation aligned to core ontology"""
    source_entity: str = Field(description="Source entity name")
    target_entity: str = Field(description="Target entity name")
    core_relation_type: str = Field(description="Core relation type from ontology")
    description: Optional[str] = Field(default=None, description="Relation description")
    confidence: float = Field(default=1.0, description="Confidence score")
    source_relations: List[str] = Field(default_factory=list, description="Original relation types")
    provenance: List[str] = Field(default_factory=list, description="Evidence sources")


class KnowledgeGraph(BaseModel):
    """Final knowledge graph structure with both raw and aligned versions"""
    # Raw extraction results (fine-grained)
    entities: Dict[str, Entity] = Field(default_factory=dict, description="Deduplicated entities indexed by name")
    relations: List[Relation] = Field(default_factory=list, description="All relations")
    
    # Aligned to core ontology (coarse-grained)
    aligned_entities: Dict[str, AlignedEntity] = Field(default_factory=dict, description="Entities aligned to ontology")
    aligned_relations: List[AlignedRelation] = Field(default_factory=list, description="Relations aligned to ontology")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the graph")


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

def _load_prompt_template(template_name: str) -> str:
    """加载提示词模板文件"""
    prompt_file = Path(__file__).parent / "prompts" / template_name
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_file}")
    
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


# 延迟加载 prompt（避免文件不存在时启动失败）
TEXT_ENTITY_EXTRACTION_PROMPT = None


def get_text_extraction_prompt() -> str:
    """获取文本实体提取 prompt"""
    global TEXT_ENTITY_EXTRACTION_PROMPT
    if TEXT_ENTITY_EXTRACTION_PROMPT is None:
        TEXT_ENTITY_EXTRACTION_PROMPT = _load_prompt_template("text_entity_extraction.txt")
    return TEXT_ENTITY_EXTRACTION_PROMPT


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_model(model_name: Optional[str] = None, temperature: float = 0.7, max_retries: int = 2) -> ChatOpenAI:
    """
    Get configured ChatOpenAI model instance.
    
    Args:
        model_name: Model name to use. If None, uses default from environment
        temperature: Temperature for the model (default: 0.7)
        max_retries: Maximum number of retries (default: 2)
        
    Returns:
        ChatOpenAI instance configured with DashScope
    """
    if model_name is None:
        model_name = "qwen-plus-latest"
    
    llm_base_url = os.getenv("LLM_BASE_URL")
    api_key = os.getenv("DASHSCOPE_API_KEY")
    
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY environment variable is not set")
    
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=llm_base_url,
        temperature=temperature,
        max_retries=max_retries,
    )


def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity between two strings using SequenceMatcher.
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        Similarity score between 0 and 1
    """
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


# =============================================================================
# CORE PIPELINE CLASSES
# =============================================================================

class DocumentLoader:
    """Load and parse document content from JSON files"""
    
    @staticmethod
    def load_from_json(file_path: str) -> List[Dict[str, Any]]:
        """
        Load document content from JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            List of content items
        """
        logger.info(f"Loading document from: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        logger.info(f"Loaded {len(content)} content items")
        return content
    
    @staticmethod
    def filter_text_items(content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter to keep only text type items.
        
        Args:
            content: List of content items
            
        Returns:
            List of text items only
        """
        text_items = [item for item in content if item.get('type') == 'text']
        logger.info(f"Filtered to {len(text_items)} text items")
        return text_items


class ChunkGrouper:
    """Group content items by dynamic chunk size"""
    
    def __init__(self, chunk_size: int = 512):
        """
        Initialize chunk grouper.
        
        Args:
            chunk_size: Target chunk size in characters (default: 512)
        """
        self.chunk_size = chunk_size
        logger.info(f"Initialized ChunkGrouper with chunk_size: {chunk_size}")
    
    def group_by_dynamic_size(self, text_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group text items by dynamic chunk size instead of fixed pages.
        
        Args:
            text_items: List of text items
            
        Returns:
            List of chunks, each containing text content and metadata
        """
        # First, sort items by page_idx to maintain order
        sorted_items = sorted(text_items, key=lambda x: (x.get('page_idx', 0), x.get('bbox', [0])[1] if x.get('bbox') else 0))
        
        chunks = []
        current_chunk_items = []
        current_chunk_text_length = 0
        current_chunk_pages = set()
        
        for item in sorted_items:
            item_text = item.get('text', '')
            item_length = len(item_text)
            page_idx = item.get('page_idx')
            
            # Check if adding this item would exceed chunk size
            if current_chunk_text_length > 0 and current_chunk_text_length + item_length > self.chunk_size:
                # Save current chunk
                if current_chunk_items:
                    chunks.append({
                        'items': current_chunk_items,
                        'text': '\n'.join([i.get('text', '') for i in current_chunk_items]),
                        'pages': sorted(current_chunk_pages),
                        'length': current_chunk_text_length
                    })
                
                # Start new chunk
                current_chunk_items = [item]
                current_chunk_text_length = item_length
                current_chunk_pages = {page_idx} if page_idx is not None else set()
            else:
                # Add to current chunk
                current_chunk_items.append(item)
                current_chunk_text_length += item_length
                if page_idx is not None:
                    current_chunk_pages.add(page_idx)
        
        # Don't forget the last chunk
        if current_chunk_items:
            chunks.append({
                'items': current_chunk_items,
                'text': '\n'.join([i.get('text', '') for i in current_chunk_items]),
                'pages': sorted(current_chunk_pages),
                'length': current_chunk_text_length
            })
        
        logger.info(f"Grouped {len(text_items)} items into {len(chunks)} chunks (target size: {self.chunk_size} chars)")
        for i, chunk in enumerate(chunks):
            logger.debug(f"  Chunk {i}: {chunk['length']} chars, pages {chunk['pages']}")
        
        return chunks


class EntityExtractor:
    """Extract entities and relations from text using LLM"""
    
    def __init__(self, model_name: Optional[str] = None, temperature: float = 0.3, max_workers: int = 3):
        """
        Initialize entity extractor.
        
        Args:
            model_name: LLM model name
            temperature: Temperature for generation (lower = more deterministic)
            max_workers: Maximum number of parallel workers (default: 3)
        """
        self.llm = get_model(model_name=model_name, temperature=temperature)
        self.structured_llm = self.llm.with_structured_output(DocumentAnalysisSchema)
        self.max_workers = max_workers
        logger.info(f"Initialized EntityExtractor with model: {model_name or 'default'}, max_workers: {max_workers}")
    
    def extract_from_chunk(self, chunk_idx: int, text_content: str, page_range: str) -> ChunkAnalysisResult:
        """
        Extract entities and relations from a single chunk.
        
        Args:
            chunk_idx: Chunk index
            text_content: Text content of the chunk
            page_range: String describing page range (e.g., "pages 0-2")
            
        Returns:
            ChunkAnalysisResult containing extracted entities and relations
        """
        logger.info(f"Extracting entities from chunk {chunk_idx} ({len(text_content)} chars, {page_range})")
        
        # Create prompt
        prompt = get_text_extraction_prompt().format(
            page_range=page_range,
            text_content=text_content
        )
        
        try:
            # Get structured output from LLM
            result = self.structured_llm.invoke(prompt)
            
            logger.info(f"Chunk {chunk_idx}: Extracted {len(result.entities)} entities, {len(result.relations)} relations")
            
            return ChunkAnalysisResult(
                chunk_idx=chunk_idx,
                page_range=page_range,
                entities=result.entities,
                relations=result.relations
            )
            
        except Exception as e:
            logger.error(f"Error extracting from chunk {chunk_idx}: {e}")
            return ChunkAnalysisResult(chunk_idx=chunk_idx, page_range=page_range)
    
    def extract_from_chunks(self, chunks: List[Dict[str, Any]], parallel: bool = True) -> List[ChunkAnalysisResult]:
        """
        Extract entities and relations from multiple chunks.
        
        Args:
            chunks: List of chunk dictionaries
            parallel: Whether to use parallel processing (default: True)
            
        Returns:
            List of ChunkAnalysisResult
        """
        if parallel and len(chunks) > 1:
            logger.info(f"Processing {len(chunks)} chunks in parallel with {self.max_workers} workers")
            return self._extract_parallel(chunks)
        else:
            logger.info(f"Processing {len(chunks)} chunks sequentially")
            return self._extract_sequential(chunks)
    
    def _extract_sequential(self, chunks: List[Dict[str, Any]]) -> List[ChunkAnalysisResult]:
        """Sequential extraction"""
        results = []
        for i, chunk in enumerate(chunks):
            text_content = chunk.get('text', '')
            if not text_content.strip():
                logger.warning(f"Chunk {i} has no text content, skipping")
                continue
            
            pages = chunk.get('pages', [])
            page_range = self._format_page_range(pages)
            result = self.extract_from_chunk(i, text_content, page_range)
            results.append(result)
        
        return results
    
    def _extract_parallel(self, chunks: List[Dict[str, Any]]) -> List[ChunkAnalysisResult]:
        """Parallel extraction using ThreadPoolExecutor"""
        results = [None] * len(chunks)
        
        def process_chunk(idx_chunk):
            idx, chunk = idx_chunk
            text_content = chunk.get('text', '')
            if not text_content.strip():
                logger.warning(f"Chunk {idx} has no text content, skipping")
                return idx, ChunkAnalysisResult(chunk_idx=idx, page_range="empty")
            
            pages = chunk.get('pages', [])
            page_range = self._format_page_range(pages)
            result = self.extract_from_chunk(idx, text_content, page_range)
            return idx, result
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(process_chunk, (i, chunk)) for i, chunk in enumerate(chunks)]
            for future in futures:
                try:
                    idx, result = future.result()
                    results[idx] = result
                except Exception as e:
                    logger.error(f"Error in parallel extraction: {e}")
        
        # Filter out None results
        return [r for r in results if r is not None]
    
    @staticmethod
    def _format_page_range(pages: List[int]) -> str:
        """Format page list into a readable range string"""
        if not pages:
            return "unknown pages"
        if len(pages) == 1:
            return f"page {pages[0]}"
        return f"pages {pages[0]}-{pages[-1]}"


class EntityDeduplicator:
    """Deduplicate and merge similar entities"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize entity deduplicator.
        
        Args:
            similarity_threshold: Threshold for considering entities as duplicates (0-1)
        """
        self.similarity_threshold = similarity_threshold
        logger.info(f"Initialized EntityDeduplicator with threshold: {similarity_threshold}")
    
    def deduplicate_entities(self, entities: List[Entity]) -> Dict[str, Entity]:
        """
        Deduplicate entities based on name similarity and type matching.
        
        Args:
            entities: List of entities to deduplicate
            
        Returns:
            Dictionary of deduplicated entities indexed by canonical name
        """
        logger.info(f"Deduplicating {len(entities)} entities")
        
        deduplicated = {}
        entity_groups = defaultdict(list)
        
        # Group entities by type for efficiency
        for entity in entities:
            entity_groups[entity.type].append(entity)
        
        # Process each type group
        for entity_type, type_entities in entity_groups.items():
            logger.debug(f"Processing {len(type_entities)} entities of type '{entity_type}'")
            
            for entity in type_entities:
                # Find matching entity
                matched = False
                for canonical_name, existing_entity in deduplicated.items():
                    if existing_entity.type != entity.type:
                        continue
                    
                    similarity = calculate_similarity(entity.name, canonical_name)
                    if similarity >= self.similarity_threshold:
                        # Merge with existing entity
                        self._merge_entities(existing_entity, entity)
                        matched = True
                        logger.debug(f"Merged '{entity.name}' into '{canonical_name}' (similarity: {similarity:.2f})")
                        break
                
                if not matched:
                    # Add as new entity
                    deduplicated[entity.name] = entity
        
        logger.info(f"Deduplication complete: {len(entities)} -> {len(deduplicated)} entities")
        return deduplicated
    
    def _merge_entities(self, target: Entity, source: Entity) -> None:
        """
        Merge source entity into target entity.
        
        Args:
            target: Target entity to merge into
            source: Source entity to merge from
        """
        # Merge descriptions (prefer longer, more detailed one)
        if source.description and (not target.description or len(source.description) > len(target.description)):
            target.description = source.description
        
        # Merge attributes (avoid duplicates)
        existing_attr_names = {attr.name for attr in target.attributes}
        for attr in source.attributes:
            if attr.name not in existing_attr_names:
                target.attributes.append(attr)
    
    def normalize_relations(self, relations: List[Relation], entity_map: Dict[str, Entity]) -> List[Relation]:
        """
        Normalize relation endpoints to use canonical entity names.
        
        Args:
            relations: List of relations to normalize
            entity_map: Mapping of canonical names to entities
            
        Returns:
            List of normalized relations
        """
        logger.info(f"Normalizing {len(relations)} relations")
        
        normalized = []
        skipped = 0
        
        for relation in relations:
            # Find canonical names for source and target
            source_canonical = self._find_canonical_name(relation.source_entity, entity_map)
            target_canonical = self._find_canonical_name(relation.target_entity, entity_map)
            
            if source_canonical and target_canonical:
                # Create normalized relation
                normalized_relation = Relation(
                    source_entity=source_canonical,
                    target_entity=target_canonical,
                    relation_type=relation.relation_type,
                    description=relation.description,
                    confidence=relation.confidence
                )
                normalized.append(normalized_relation)
            else:
                skipped += 1
                logger.debug(f"Skipped relation: {relation.source_entity} -> {relation.target_entity} (entity not found)")
        
        logger.info(f"Normalized {len(normalized)} relations, skipped {skipped}")
        return normalized
    
    def _find_canonical_name(self, entity_name: str, entity_map: Dict[str, Entity]) -> Optional[str]:
        """
        Find canonical name for an entity.
        
        Args:
            entity_name: Entity name to look up
            entity_map: Map of canonical names to entities
            
        Returns:
            Canonical entity name or None if not found
        """
        # Direct match
        if entity_name in entity_map:
            return entity_name
        
        # Fuzzy match
        best_match = None
        best_similarity = 0
        
        for canonical_name in entity_map.keys():
            similarity = calculate_similarity(entity_name, canonical_name)
            if similarity >= self.similarity_threshold and similarity > best_similarity:
                best_match = canonical_name
                best_similarity = similarity
        
        return best_match


class OntologyAligner:
    """Align entities and relations to core ontology"""
    
    # Entity type mapping rules (from fine-grained types to core types)
    ENTITY_TYPE_MAPPING = {
        # Company related
        'company': CoreEntityType.COMPANY,
        'organization': CoreEntityType.COMPANY,
        'startup': CoreEntityType.COMPANY,
        'firm': CoreEntityType.COMPANY,
        'corporation': CoreEntityType.COMPANY,
        'enterprise': CoreEntityType.COMPANY,
        'institution': CoreEntityType.COMPANY,
        'investor': CoreEntityType.COMPANY,
        'investment_firm': CoreEntityType.COMPANY,
        'fund': CoreEntityType.COMPANY,
        'university': CoreEntityType.COMPANY,
        'research_lab': CoreEntityType.COMPANY,
        
        # Person related
        'person': CoreEntityType.PERSON,
        'founder': CoreEntityType.PERSON,
        'ceo': CoreEntityType.PERSON,
        'executive': CoreEntityType.PERSON,
        'researcher': CoreEntityType.PERSON,
        'scientist': CoreEntityType.PERSON,
        'engineer': CoreEntityType.PERSON,
        'expert': CoreEntityType.PERSON,
        'author': CoreEntityType.PERSON,
        'team_member': CoreEntityType.PERSON,
        
        # Technology related
        'technology': CoreEntityType.TECHNOLOGY,
        'technique': CoreEntityType.TECHNOLOGY,
        'algorithm': CoreEntityType.TECHNOLOGY,
        'method': CoreEntityType.TECHNOLOGY,
        'framework': CoreEntityType.TECHNOLOGY,
        'platform': CoreEntityType.TECHNOLOGY,
        'system': CoreEntityType.TECHNOLOGY,
        'model': CoreEntityType.TECHNOLOGY,
        'tool': CoreEntityType.TECHNOLOGY,
        'software': CoreEntityType.TECHNOLOGY,
        'hardware': CoreEntityType.TECHNOLOGY,
        'device': CoreEntityType.TECHNOLOGY,
        'material': CoreEntityType.TECHNOLOGY,
        'component': CoreEntityType.TECHNOLOGY,
        
        # Product related
        'product': CoreEntityType.PRODUCT,
        'service': CoreEntityType.PRODUCT,
        'platform': CoreEntityType.PRODUCT,
        'application': CoreEntityType.PRODUCT,
        'app': CoreEntityType.PRODUCT,
        'software': CoreEntityType.PRODUCT,
        'system': CoreEntityType.PRODUCT,
        'solution': CoreEntityType.PRODUCT,
        'tool': CoreEntityType.PRODUCT,
        
        # TagConcept related
        'industry': CoreEntityType.TAG_CONCEPT,
        'domain': CoreEntityType.TAG_CONCEPT,
        'field': CoreEntityType.TAG_CONCEPT,
        'sector': CoreEntityType.TAG_CONCEPT,
        'category': CoreEntityType.TAG_CONCEPT,
        'tag': CoreEntityType.TAG_CONCEPT,
        'tag_concept': CoreEntityType.TAG_CONCEPT,
        'concept': CoreEntityType.TAG_CONCEPT,
        'topic': CoreEntityType.TAG_CONCEPT,
        'area': CoreEntityType.TAG_CONCEPT,
        'market': CoreEntityType.TAG_CONCEPT,
        'segment': CoreEntityType.TAG_CONCEPT,
        'industry_segment': CoreEntityType.TAG_CONCEPT,
        'application_scenario': CoreEntityType.TAG_CONCEPT,
        
        # Event related
        'event': CoreEntityType.EVENT,
        'news': CoreEntityType.EVENT,
        'announcement': CoreEntityType.EVENT,
        'financing': CoreEntityType.EVENT,
        'investment': CoreEntityType.EVENT,
        'acquisition': CoreEntityType.EVENT,
        'merger': CoreEntityType.EVENT,
        'partnership': CoreEntityType.EVENT,
        'collaboration': CoreEntityType.EVENT,
        'launch': CoreEntityType.EVENT,
        'release': CoreEntityType.EVENT,
        
        # Signal related
        'signal': CoreEntityType.SIGNAL,
        'indicator': CoreEntityType.SIGNAL,
        'metric': CoreEntityType.SIGNAL,
        'trend': CoreEntityType.SIGNAL,
        
        # Other types (will be filtered in aligned version)
        'patent': CoreEntityType.OTHER,
        'paper': CoreEntityType.OTHER,
        'report': CoreEntityType.OTHER,
        'dataset': CoreEntityType.OTHER,
        'standard': CoreEntityType.OTHER,
        'location': CoreEntityType.OTHER,
    }
    
    # Relation type mapping rules
    RELATION_TYPE_MAPPING = {
        # Founding/Leadership
        'founded_by': CoreRelationType.FOUNDED_BY,
        'created_by': CoreRelationType.FOUNDED_BY,
        'established_by': CoreRelationType.FOUNDED_BY,
        'led_by': CoreRelationType.FOUNDED_BY,
        
        # Investment
        'invested_by': CoreRelationType.INVESTED_BY,
        'funded_by': CoreRelationType.INVESTED_BY,
        'backed_by': CoreRelationType.INVESTED_BY,
        'financed_by': CoreRelationType.INVESTED_BY,
        'invested_in': CoreRelationType.INVESTED_BY,
        
        # Employment
        'works_at': CoreRelationType.WORKS_AT,
        'employed_by': CoreRelationType.WORKS_AT,
        'member_of': CoreRelationType.WORKS_AT,
        'serves_at': CoreRelationType.WORKS_AT,
        
        # Technology usage
        'uses_technology': CoreRelationType.USES_TECHNOLOGY,
        'uses': CoreRelationType.USES_TECHNOLOGY,
        'adopts': CoreRelationType.USES_TECHNOLOGY,
        'implements': CoreRelationType.USES_TECHNOLOGY,
        'applies': CoreRelationType.USES_TECHNOLOGY,
        'leverages': CoreRelationType.USES_TECHNOLOGY,
        
        # Industry/Segment
        'in_segment': CoreRelationType.IN_SEGMENT,
        'in_industry': CoreRelationType.IN_SEGMENT,
        'in_field': CoreRelationType.IN_SEGMENT,
        'operates_in': CoreRelationType.IN_SEGMENT,
        'focuses_on': CoreRelationType.IN_SEGMENT,
        'targets': CoreRelationType.IN_SEGMENT,
        
        # Competition
        'competes_with': CoreRelationType.COMPETES_WITH,
        'rival_of': CoreRelationType.COMPETES_WITH,
        'competitor_of': CoreRelationType.COMPETES_WITH,
        
        # Partnership
        'partners_with': CoreRelationType.PARTNERS_WITH,
        'collaborates_with': CoreRelationType.PARTNERS_WITH,
        'cooperates_with': CoreRelationType.PARTNERS_WITH,
        'works_with': CoreRelationType.PARTNERS_WITH,
        
        # Research
        'researches': CoreRelationType.RESEARCHES,
        'studies': CoreRelationType.RESEARCHES,
        'investigates': CoreRelationType.RESEARCHES,
        'develops': CoreRelationType.RESEARCHES,
        
        # Education
        'educated_at': CoreRelationType.EDUCATED_AT,
        'studied_at': CoreRelationType.EDUCATED_AT,
        'graduated_from': CoreRelationType.EDUCATED_AT,
        
        # Hierarchy
        'part_of': CoreRelationType.PART_OF,
        'subset_of': CoreRelationType.PART_OF,
        'component_of': CoreRelationType.PART_OF,
        'belongs_to': CoreRelationType.PART_OF,
        
        # Related
        'related_to': CoreRelationType.RELATED_TO,
        'associated_with': CoreRelationType.RELATED_TO,
        'connected_to': CoreRelationType.RELATED_TO,
        
        # Application
        'applied_in': CoreRelationType.APPLIED_IN,
        'used_in': CoreRelationType.APPLIED_IN,
        
        # Events
        'involves': CoreRelationType.INVOLVES,
        'includes': CoreRelationType.INVOLVES,
        'affects': CoreRelationType.INVOLVES,
        
        # Location
        'located_in': CoreRelationType.LOCATED_IN,
        'based_in': CoreRelationType.LOCATED_IN,
        'headquartered_in': CoreRelationType.LOCATED_IN,
    }
    
    def __init__(self):
        """Initialize ontology aligner"""
        logger.info("Initialized OntologyAligner")
    
    def align_entities(self, entities: Dict[str, Entity]) -> Dict[str, AlignedEntity]:
        """
        Align fine-grained entities to core ontology types with structured fields.
        
        Args:
            entities: Dictionary of deduplicated entities
            
        Returns:
            Dictionary of aligned entities (keyed by name)
        """
        logger.info(f"Aligning {len(entities)} entities to core ontology")
        
        aligned_entities = {}
        type_distribution = {}
        
        for name, entity in entities.items():
            # Map to core type
            core_type = self._map_entity_type(entity.type)
            type_distribution[core_type] = type_distribution.get(core_type, 0) + 1
            
            # Skip "Other" type entities
            if core_type == CoreEntityType.OTHER:
                continue
            
            # Extract structured fields based on core type
            fields = self._extract_structured_fields(entity, core_type)
            
            # Create aligned entity
            aligned_entity = AlignedEntity(
                name=name,
                core_type=core_type,
                description=entity.description,
                source_entities=[name],
                **fields  # Unpack structured fields
            )
            
            aligned_entities[name] = aligned_entity
        
        logger.info(f"Aligned entities distribution (before filtering): {type_distribution}")
        logger.info(f"Aligned entities count (after filtering Other): {len(aligned_entities)}")
        return aligned_entities
    
    def align_relations(
        self,
        relations: List[Relation],
        raw_entities: Dict[str, Entity],
        aligned_entities: Dict[str, AlignedEntity]
    ) -> List[AlignedRelation]:
        """
        Align relations to core ontology types (using entity names as identifiers).
        
        Args:
            relations: List of normalized relations
            raw_entities: Original entity map (for lookup)
            aligned_entities: Aligned entity map (keyed by name)
            
        Returns:
            List of aligned relations
        """
        logger.info(f"Aligning {len(relations)} relations to core ontology")
        
        aligned_relations = []
        type_distribution = {}
        skipped = 0
        
        for relation in relations:
            # Check if both entities exist in aligned entities
            if relation.source_entity not in aligned_entities or relation.target_entity not in aligned_entities:
                skipped += 1
                logger.debug(f"Skipped relation: {relation.source_entity} -> {relation.target_entity} (entity not found)")
                continue
            
            # Map to core relation type
            core_relation_type = self._map_relation_type(relation.relation_type)
            type_distribution[core_relation_type] = type_distribution.get(core_relation_type, 0) + 1
            
            # Create aligned relation
            aligned_relation = AlignedRelation(
                source_entity=relation.source_entity,
                target_entity=relation.target_entity,
                core_relation_type=core_relation_type,
                description=relation.description,
                confidence=relation.confidence,
                source_relations=[relation.relation_type],
                provenance=[]
            )
            
            aligned_relations.append(aligned_relation)
        
        logger.info(f"Aligned {len(aligned_relations)} relations, skipped {skipped}")
        logger.info(f"Aligned relations distribution: {type_distribution}")
        
        return aligned_relations
    
    def _map_entity_type(self, raw_type: str) -> str:
        """Map raw entity type to core ontology type"""
        raw_type_lower = raw_type.lower().strip()
        
        # Direct mapping
        if raw_type_lower in self.ENTITY_TYPE_MAPPING:
            return self.ENTITY_TYPE_MAPPING[raw_type_lower]
        
        # Fuzzy matching for compound types
        for pattern, core_type in self.ENTITY_TYPE_MAPPING.items():
            if pattern in raw_type_lower or raw_type_lower in pattern:
                return core_type
        
        # Fallback
        logger.debug(f"Unmapped entity type: {raw_type} -> Other")
        return CoreEntityType.OTHER
    
    def _map_relation_type(self, raw_relation: str) -> str:
        """Map raw relation type to core ontology relation type"""
        raw_relation_lower = raw_relation.lower().strip().replace(' ', '_')
        
        # Direct mapping
        if raw_relation_lower in self.RELATION_TYPE_MAPPING:
            return self.RELATION_TYPE_MAPPING[raw_relation_lower]
        
        # Fuzzy matching
        for pattern, core_relation in self.RELATION_TYPE_MAPPING.items():
            if pattern in raw_relation_lower or raw_relation_lower in pattern:
                return core_relation
        
        # Fallback
        logger.debug(f"Unmapped relation type: {raw_relation} -> other")
        return CoreRelationType.OTHER
    
    def _extract_structured_fields(self, entity: Entity, core_type: str) -> Dict[str, Any]:
        """Extract structured fields based on core entity type"""
        # Convert attributes list to dict
        attr_dict = {attr.name: attr.value for attr in entity.attributes}
        
        fields = {}
        
        if core_type == CoreEntityType.COMPANY:
            fields['legal_name'] = attr_dict.get('legal_name')
            fields['founded_date'] = attr_dict.get('founded_date') or attr_dict.get('founding_date')
            fields['stage'] = attr_dict.get('stage') or attr_dict.get('funding_stage')
            fields['industry'] = attr_dict.get('industry')
            fields['location'] = attr_dict.get('location') or attr_dict.get('region')
            fields['website'] = attr_dict.get('website')
            
        elif core_type == CoreEntityType.PERSON:
            edu = attr_dict.get('education') or attr_dict.get('education_background')
            fields['education'] = [edu] if edu and isinstance(edu, str) else []
            pos = attr_dict.get('position') or attr_dict.get('role')
            fields['positions'] = [pos] if pos and isinstance(pos, str) else []
            exp = attr_dict.get('expertise')
            fields['expertise'] = [exp] if exp and isinstance(exp, str) else []
            
        elif core_type == CoreEntityType.TECHNOLOGY:
            fields['application_domain'] = attr_dict.get('application_domain') or attr_dict.get('domain')
            chars = attr_dict.get('technical_characteristics') or attr_dict.get('characteristics')
            fields['technical_characteristics'] = [chars] if chars and isinstance(chars, str) else []
            fields['maturity_level'] = attr_dict.get('maturity_level') or attr_dict.get('maturity')
            
        elif core_type == CoreEntityType.PRODUCT:
            fields['version'] = attr_dict.get('version')
            feats = attr_dict.get('features')
            fields['features'] = [feats] if feats and isinstance(feats, str) else []
            fields['application_domain'] = attr_dict.get('application_domain')
            
        return fields


class KnowledgeGraphBuilder:
    """Build knowledge graph from extracted entities and relations"""
    
    @staticmethod
    def build(
        deduplicated_entities: Dict[str, Entity],
        normalized_relations: List[Relation],
        aligned_entities: Optional[Dict[str, AlignedEntity]] = None,
        aligned_relations: Optional[List[AlignedRelation]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeGraph:
        """
        Build knowledge graph structure with both raw and aligned versions.
        
        Args:
            deduplicated_entities: Deduplicated entities (raw)
            normalized_relations: Normalized relations (raw)
            aligned_entities: Entities aligned to ontology
            aligned_relations: Relations aligned to ontology
            metadata: Optional metadata
            
        Returns:
            KnowledgeGraph object
        """
        if metadata is None:
            metadata = {}
        
        if aligned_entities is None:
            aligned_entities = {}
        if aligned_relations is None:
            aligned_relations = []
        
        # Add statistics for raw entities
        metadata['total_entities'] = len(deduplicated_entities)
        metadata['total_relations'] = len(normalized_relations)
        metadata['entity_types'] = list(set(e.type for e in deduplicated_entities.values()))
        metadata['relation_types'] = list(set(r.relation_type for r in normalized_relations))
        
        # Add statistics for aligned entities
        metadata['total_aligned_entities'] = len(aligned_entities)
        metadata['total_aligned_relations'] = len(aligned_relations)
        if aligned_entities:
            metadata['aligned_entity_types'] = list(set(e.core_type for e in aligned_entities.values()))
        if aligned_relations:
            metadata['aligned_relation_types'] = list(set(r.core_relation_type for r in aligned_relations))
        
        metadata['build_time'] = datetime.now().isoformat()
        
        graph = KnowledgeGraph(
            entities=deduplicated_entities,
            relations=normalized_relations,
            aligned_entities=aligned_entities,
            aligned_relations=aligned_relations,
            metadata=metadata
        )
        
        logger.info(f"Built knowledge graph: {len(deduplicated_entities)} raw entities, {len(aligned_entities)} aligned entities")
        logger.info(f"                       {len(normalized_relations)} raw relations, {len(aligned_relations)} aligned relations")
        return graph


# =============================================================================
# MAIN PIPELINE
# =============================================================================

class TextKnowledgeGraphPipeline:
    """Complete pipeline for text-based knowledge graph extraction"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.3,
        similarity_threshold: float = 0.85,
        chunk_size: int = 512,
        max_workers: int = 3,
        parallel: bool = True
    ):
        """
        Initialize pipeline.
        
        Args:
            model_name: LLM model name
            temperature: Temperature for LLM generation
            similarity_threshold: Threshold for entity deduplication
            chunk_size: Target chunk size in characters (default: 512)
            max_workers: Maximum number of parallel workers (default: 3)
            parallel: Whether to use parallel processing (default: True)
        """
        self.loader = DocumentLoader()
        self.grouper = ChunkGrouper(chunk_size=chunk_size)
        self.extractor = EntityExtractor(model_name=model_name, temperature=temperature, max_workers=max_workers)
        self.deduplicator = EntityDeduplicator(similarity_threshold=similarity_threshold)
        self.aligner = OntologyAligner()
        self.builder = KnowledgeGraphBuilder()
        self.parallel = parallel
        
        logger.info(f"Initialized TextKnowledgeGraphPipeline (chunk_size={chunk_size}, parallel={parallel}, max_workers={max_workers})")
    
    def process_document(self, json_path: str) -> KnowledgeGraph:
        """
        Process a document and extract knowledge graph.
        
        Args:
            json_path: Path to JSON file containing parsed document
            
        Returns:
            KnowledgeGraph object
        """
        logger.info(f"=" * 80)
        logger.info(f"Processing document: {json_path}")
        logger.info(f"=" * 80)
        
        # Step 1: Load document
        content = self.loader.load_from_json(json_path)
        text_items = self.loader.filter_text_items(content)
        
        # Step 2: Group by dynamic chunk size
        chunks = self.grouper.group_by_dynamic_size(text_items)
        
        # Step 3: Extract entities and relations from each chunk (with optional parallelization)
        chunk_results = self.extractor.extract_from_chunks(chunks, parallel=self.parallel)
        
        # Step 4: Aggregate all entities and relations
        all_entities = []
        all_relations = []
        
        for result in chunk_results:
            all_entities.extend(result.entities)
            all_relations.extend(result.relations)
        
        logger.info(f"Total extracted: {len(all_entities)} entities, {len(all_relations)} relations")
        
        # Step 5: Deduplicate entities
        deduplicated_entities = self.deduplicator.deduplicate_entities(all_entities)
        
        # Step 6: Normalize relations
        normalized_relations = self.deduplicator.normalize_relations(all_relations, deduplicated_entities)
        
        # Step 7: Align entities to core ontology
        aligned_entities = self.aligner.align_entities(deduplicated_entities)
        
        # Step 8: Align relations to core ontology
        aligned_relations = self.aligner.align_relations(
            normalized_relations,
            deduplicated_entities,
            aligned_entities
        )
        
        # Step 9: Build knowledge graph (with both raw and aligned versions)
        metadata = {
            'source_file': json_path,
            'total_chunks': len(chunks),
            'total_text_items': len(text_items),
            'chunk_size': self.grouper.chunk_size,
            'parallel_processing': self.parallel
        }
        
        graph = self.builder.build(
            deduplicated_entities,
            normalized_relations,
            aligned_entities,
            aligned_relations,
            metadata
        )
        
        logger.info(f"=" * 80)
        logger.info(f"Pipeline complete: Built graph with {len(graph.entities)} entities and {len(graph.relations)} relations")
        logger.info(f"=" * 80)
        
        return graph
    
    def save_graph(self, graph: KnowledgeGraph, output_path: str) -> None:
        """保存知识图谱到 JSON 文件（raw 和 aligned 两个版本）
        
        Args:
            graph: KnowledgeGraph 对象
            output_path: 输出文件基础路径（会生成两个文件）
        """
        from pathlib import Path
        
        # 生成统一的文件名
        base_path = Path(output_path)
        base_name = base_path.stem.replace("_kg", "").replace("_content_list", "")
        raw_path = base_path.parent / f"{base_name}_text_raw.json"
        aligned_path = base_path.parent / f"{base_name}_text_kg_aligned.json"
        
        logger.info(f"保存知识图谱到:")
        logger.info(f"  - Raw 版本: {raw_path}")
        logger.info(f"  - Aligned 版本: {aligned_path}")
        
        # 准备 raw 版本数据
        raw_data = {
            'metadata': {
                # 通用字段
                'source_file': graph.metadata.get('source_file'),
                'pipeline_type': 'text',
                'pipeline_version': '2.0',
                'build_time': graph.metadata.get('build_time'),
                
                # 统计信息
                'total_entities': graph.metadata.get('total_entities'),
                'total_relations': graph.metadata.get('total_relations'),
                'entity_types': graph.metadata.get('entity_types', []),
                'relation_types': graph.metadata.get('relation_types', []),
                
                # Text pipeline 特有字段
                'total_chunks': graph.metadata.get('total_chunks'),
                'total_text_items': graph.metadata.get('total_text_items'),
                'chunk_size': graph.metadata.get('chunk_size'),
                'parallel_processing': graph.metadata.get('parallel_processing')
            },
            'entities': {
                name: {
                    'name': entity.name,
                    'type': entity.type,
                    'description': entity.description,
                    'attributes': [
                        {'name': attr.name, 'value': attr.value}
                        for attr in entity.attributes
                    ]
                }
                for name, entity in graph.entities.items()
            },
            'relations': [
                {
                    'source_entity': relation.source_entity,
                    'target_entity': relation.target_entity,
                    'relation_type': relation.relation_type,
                    'description': relation.description,
                    'confidence': relation.confidence
                }
                for relation in graph.relations
            ]
        }
        
        # 准备 aligned 版本数据
        aligned_data = {
            'metadata': {
                # 通用字段
                'source_file': graph.metadata.get('source_file'),
                'pipeline_type': 'text',
                'data_source': 'text_pipeline',
                'ontology_version': 'v1.2.1',
                'build_time': graph.metadata.get('build_time'),
                
                # 统计信息
                'total_aligned_entities': graph.metadata.get('total_aligned_entities'),
                'total_aligned_relations': graph.metadata.get('total_aligned_relations'),
                'aligned_entity_types': graph.metadata.get('aligned_entity_types', []),
                'aligned_relation_types': graph.metadata.get('aligned_relation_types', []),
                
                # 核心类型定义
                'core_entity_types': ['Company', 'Person', 'Technology', 'Product', 'TagConcept', 'Event', 'Signal', 'Other'],
                'core_relation_types': [
                    'founded_by', 'invested_by', 'uses_technology', 'in_segment',
                    'competes_with', 'partners_with', 'works_at', 'researches',
                    'educated_at', 'part_of', 'related_to', 'applied_in',
                    'involves', 'located_in', 'other'
                ]
            },
            'aligned_entities': {
                name: entity.model_dump(exclude_none=True)
                for name, entity in graph.aligned_entities.items()
            },
            'aligned_relations': [
                relation.model_dump(exclude_none=True)
                for relation in graph.aligned_relations
            ]
        }
        
        # 保存 raw 版本
        with open(raw_path, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Raw 版本已保存: {len(graph.entities)} 个实体, {len(graph.relations)} 个关系")
        
        # 保存 aligned 版本
        with open(aligned_path, 'w', encoding='utf-8') as f:
            json.dump(aligned_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Aligned 版本已保存: {len(graph.aligned_entities)} 个实体, {len(graph.aligned_relations)} 个关系")


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

def main():
    """Main entry point for command line usage"""
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description='Extract knowledge graph from document')
    parser.add_argument('input', type=str, help='Input JSON file path')
    parser.add_argument('-o', '--output', type=str, help='Output JSON file path (default: input_kg.json)')
    parser.add_argument('-m', '--model', type=str, default=None, help='Model name to use')
    parser.add_argument('-t', '--temperature', type=float, default=0.3, help='Temperature (default: 0.3)')
    parser.add_argument('-s', '--similarity', type=float, default=0.85, help='Similarity threshold (default: 0.85)')
    parser.add_argument('-c', '--chunk-size', type=int, default=512, help='Chunk size in characters (default: 512)')
    parser.add_argument('-w', '--max-workers', type=int, default=3, help='Max parallel workers (default: 3)')
    parser.add_argument('--no-parallel', action='store_true', help='Disable parallel processing')
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        # 不需要添加 _kg 后缀，save_graph 会自动处理
        output_path = str(input_path.parent / f"{input_path.stem}.json")
    
    # Run pipeline
    pipeline = TextKnowledgeGraphPipeline(
        model_name=args.model,
        temperature=args.temperature,
        similarity_threshold=args.similarity,
        chunk_size=args.chunk_size,
        max_workers=args.max_workers,
        parallel=not args.no_parallel
    )
    
    graph = pipeline.process_document(args.input)
    pipeline.save_graph(graph, output_path)
    
    from pathlib import Path
    base_path = Path(output_path)
    # 使用统一的文件名格式
    base_name = base_path.stem.replace("_kg", "").replace("_content_list", "")
    raw_path = base_path.parent / f"{base_name}_text_raw.json"
    aligned_path = base_path.parent / f"{base_name}_text_kg_aligned.json"
    
    print(f"\n✓ Knowledge graph extraction complete!")
    print(f"\n📊 Raw Version (细粒度):")
    print(f"  - Entities: {len(graph.entities)}")
    print(f"  - Relations: {len(graph.relations)}")
    print(f"  - Entity Types: {len(graph.metadata.get('entity_types', []))}")
    print(f"  - Output: {raw_path}")
    print(f"\n🎯 Aligned Version (标准化):")
    print(f"  - Entities: {len(graph.aligned_entities)}")
    print(f"  - Relations: {len(graph.aligned_relations)}")
    print(f"  - Core Entity Types: {len(graph.metadata.get('aligned_entity_types', []))}")
    print(f"  - Output: {aligned_path}")


if __name__ == "__main__":
    main()
