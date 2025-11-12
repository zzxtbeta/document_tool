1.维护 Tech Context
Al Coding 发展到现在 bottleneck 不在于模型而是人类的 guidance 是否完善。即大部分情况下问题是:AICoding 出来的代码并没有和你的“真实"想法对齐。由于 AI没有读心术，我们需要提供对应的 context 来解决这些问题。
CONTEXT ENGINEERING
NCeG
LLMs cannot read minds && Bad Context
Context Engineering
在反复几次手敲 prompt后，我会维护一个简单的TechContext，存在我的iCloud 上，方便任何情况下的复制粘贴。一个简单的 Tech Context Example，你可以根据你的需求任意修改，包括添加上你的一些小偏好

基于该 Context 你可以在后续任意步骤中轻松得让 AI对齐你开发的大方向。换言之，你在手动的维护 personalmemory.
除了 Tech Context外我还喜欢维护 Dev Context，例如代码风格，系统设计偏好(目前更普遍的是放在 AGENTS.md 文件下)但 Dev Context是和项目主题挂钩的，全栈开发和 Al Agent 的 Dev Context 是不同的。由于我不希望引入一些无关上下文，我目前会选择手动的维护在自己的 Obsidian上，按需粘贴或者放在代码库的 AGENTS.md 中。


2. Talk to Design Docs
当模型的能力超过“那个边界“后(我认为 claudeSonnet4和 GPT5-Codex-High 都满足条件)，编程的范式已经在逐步转移至“自然语言编程"。例如最近比较火的 Repo spec-kit 教你如何编撰完善的文档来进行AlCoding，由于我没具体用过该项目无法给出详细的见解。
(spec-kit
但就我个人而言，这种基于自然语言编码的范式极大的利用了我的零碎时间。因为它相较于传统的编码范式最大优势是极简单/极快速的开始。传统的编码是一个冷后动的过程，你需要一些 warmup。例如打开电脑，打开IDE，构思并以具体的语言编写代码。但基于自然语言编程的范式可以在任意时间开始编程，你只需要把思考和目标等 prompt写在备忘录等文本编辑软件中，在有空寸让 AI帮你进行编码。
当然，自然语言编程一定会出现各种 corner case，我们对此需要宽容一些。就像你以前在使用编程语言进行编码时会出现许多 bug，当你用 prompt进行编码时这同样不可避免。但这同样是一个积累的过程，这就是为什么 Context 如此重要。除了模型本身能力的增长外，你相较于其他人的优势很大一部分来自你总结的context。
所以，目前对我而言最重要的是如何构建一个准确，符合 Al Coding Best Practice 的设计文档?我目前的实践是和 LLM 进行对话并在进行多轮对话后让 LLM 生成规范的设计文档作为后续 Al Coding 的基石。我的大致流程如下:
1.打开 Claude APP，粘贴 Tech Context 然后简述我的设计目标和它一步步讨论系统架构，细节，以及让它提出当前设计中可能的问题和存在模糊/歧义


2.你可以很简单地在一个 chat session 中 深入任何细节 或 解决任何困惑。在你觉得这个设计足够完善后便可以让 Claude 基于当前 session 的 chat history生成最终的 design docs。
3.在与 LLM 交流的过程中，任何收获和反思都可以手动更新到 Tech/Dev Context中。这就是产生技术复利的关键，维护良好的 Tech/Dev Context可以以在后续的项目开发中节省大量的时间。
可能有相当多的人会认为总结自己的 Context其实不重要，因为模型能力的发展会让这些Context 没有任何价值。我也无法预期未来模型的发展，我也认真思考过这个问题，简单讲讲我的Ỹ停理解:
我们维护个人的 Context 很多时候并不是为了帮模型提升性能。而是为了帮模型对齐你自己。模型的能力就目前和未来而言一定是超过绝大部分个人的。Context是为了让模型以你能理解的方式给出回答。所以构建 Context 是必要的(让模型对齐你的能力)，反思和更新Context也是必要的(让你对齐模型的能力)二者缺一不可。
3. Project level && Feature level我很久之前把 Vibe Coding 划分为两类(参考上一次的Zen of Vibe Coding 的博客，但具体内容可能过时了不少那时候的 Coding Agent 能力远比不上如今):
Project-Level，整体项目相关的，涉及多个/复杂/耦合盡们维护个人的 Context 很多时候并不是为了分与讨论，比如“设计具有某个功能的插件/应用"。
Feature-Level，具体功能相关的，涉及单个/少数

Feature-Level，具体功能相关的，涉及单个/少数/独立的问题。特点是需求比较清晰，可以参考大部分 GitHub 中的 issue，比如“修复某个因为 XX导致的 bug"。
但为了不切换 context 我把之前博客中的图也迁移过来，让大家有个大致的了解。
Idea
不经思考的
Vide Coding
Project-Level Issues
Core of Vibe Coding
Human Thinking
Feoture-Level I$SUES
"Zen of Vibe Coding
Knowledge System
Uedate
Feedback
Chud 37 $onnet
4 Gomini 2.5 Fash Prevlaw
6
04-17
带
国40
由
FAIL
混乱的项目架构
无法继承的知识体系
无从下手的各式 Bug
良好的设计文档忠和项目架构
Review
我简单介绍下我是如何分别处理这两类问题的:
3.1 Feature level issue
关于 Feature level问题的解决，我的思路一直是固定的。这也是我觉得 AlCoding 中很重要的一部分:当需要你解决细节问题时，你最好真的能解决。这是 AICoding 最后一公里以及 Demo to Production 中最重要的一环。
因为 Learn by doing，Al Coding 现在会跳过绝大部分的 doing 步骤，如果连 feature level的问题你都完全的因为 Learn by doing，Al Coding 现在会跳过绝大部分的 doing 步骤，如果连 featurelevel的问题你都完全的依赖 AI，你很难有任何进步，相反你绝大部分能力都会退步。最开始有段时间，我会完全利用 AI做整个项目，但是后果是我在 debug 时也完全依赖 AI，导致在一些其实很简单挿方的问题上浪费非常多的时间(AI有时会一直无法解决某些问题)同时心态非常差(因为解决问题就像在抽卡，你无法预期能否解决这个问题，以及何时解决这个问题)同时，长远来看我会非常浮躁且没有收获任何长尾价值。
所以对我个人，我会保证我理解这个问题的完整上下文，我会尝试提出解决方案。使用 A去按我的思路去解决问题，而非它替我解决这个问题。所以我会用 cursor的 chat 功能来解决 featurelevel的问题以确保我最大程度的掌握这些细节。
同时。这类问题常出现在 A1完成整个项目代码后，你在实际运行中发现的。这可能说明你最开始的 design 中并没有 cover 这一部分。这恰好是你值得学习的部分，你可以反思并更新 Context。
是你的 design 中缺少了什么吗?
是你的描述(Prompt)存在歧义吗?
是你需要补充启发式的 guidance 吗?如果需要你是否需要维护属于自己的 AGENTS.md ?
这是你修正 Tech/Dev Context与 Design Docs 最重要的环节。
3.2 Project level issue
Project level的问题范围有点太广了。目前我的实践如前文提到的主要是:维护Context→交流生成 DesignDocs →AlCoding 编写→反思并更新 Context&Design.
更具体的:
如果是 FullStack，我会用 bolt.new 进行 MVP 开发，在 chatbot 中调优几轮后 download 在本地用cursor 解决 feature level 的问题。
如果是偏 Research& Open Source，我会选择让Codex Review Design Docs 生成具体的开发Plan，让 Claude Code 基于 Plan 开发，最终让Codex进行Review(关于Codex和 Claude Code的对比见文末)
4.Summary
这些内容包含了绝大部分我 AlCoding的 practices。除此之外也没有更多特别的地方。在调研部分我会同时启动Gemini/OpenAl/Claude的DeepResearch，目前我更喜欢 Claude Research，-部分原因是使用体验,一部分原因是我拆解过它的具体架构:Multi-AgentSystem，一篇就够了。
关于 Codex 和 Claude Code 的对比，复制我之前的某个评论:
我这里只能对比 claude sonnet4.5/gpt5-codex-high.cc 在 agent architecture 上做的很好，执行的非常快，但是默认的风格是过度工程化，过度设计，即使你给出很详细的设计文档，但是 cc还是会在一些你没完全 define 好的细节处进行过度工程化，需要你提前设置许多 rules。
codex 是纯模型很强，有种大巧不工的感觉，在implementation上非常克制和恰当，很难具体描述这种感觉。大致来说就是可用性非常高，不会过度设计。适合做impl和refactor(如果让cc的refactor 大概率是越做越奇怪)

使你给出很详细的设计文档，但是 cc 还是会在一些你没完全 define 好的细节处进行过度工程化，需要你提前设置许多 rules。
codex 是纯模型很强，有种大巧不工的感觉，在implementation 上非常克制和恰当，很难具体描述这种感觉。大致来说就是可用性非常高，不会过度设计。适合做impl和refactor(如果让 cc 的refactor 大概率是越做越奇怪)
所以推荐结合一起使用:
1.如果是 from scratch，我会先 draft 非常详细的设计文档，这对于 codex&cc都很重要。让codexrefine&生成 Plan.md ->ccimplementation(写的快)-->codexreview(如果发现 cc 它写的问题很大，直接清空让 codex 写)
2如果只是 feature level的，我会用 cursor 哈哈哈 保证自己对 feature level 问题的完整掌握，否则会陷入 vibe coding 常见的原地打转情况。
cc 在 agent architecture & context engineering 上的深度优化在未来肯定是有它对应的生态位。比如Anthropic 现在在 beta的 memory tool 和 contextediting。如果这些功能更新到正式版的cc中，那么在某些特殊场景下会和 codex 拉很大的差距。推荐阅读下面这个小博客，非常有意思。


🥕🥕Highlight
———
可能有相当多的人会认为总结自己的 Context 其实不重要，因为模型能力的发展会让这些 Context 没有任何价值。我也无法预期未来模型的发展，我也认真思考过这个问题，简单讲讲我的理解：
	
我们维护个人的 Context 很多时候并不是为了帮模型提升性能。而是✨为了帮模型对齐你自己。模型的能力就目前和未来而言一定是超过绝大部分个人的。Context 是为了让模型以你能理解的方式给出回答。所以✨构建 Context 是必要的（让模型对齐你的能力），反思和更新 Context 也是必要的（让你对齐模型的能力）二者缺一不可。


---

Anthropic 最佳实践: AICoding 新范式
1.引言:AI编程的下一个阶段
当前，以 Cursor 为代表的 AI 编程助手已成为许多开发者的标配。它们在代码补全、函数生成等“微观任务"(如我之前博客所说，feature-level)上表现出色。然而，当我们将视角拉远，思考更复杂的开发流程--如原型构建、功能实现、代码重构--我们面临一个更深层次的问题:开发者与 AI之间最佳的协作范式是怎样的?解决 Project-Level 问题的最佳实践是什么?
如何解决这两个问题不仅对专业的工程师有益同时对编程小白更有价值。因为这涉及到如何借助 AI 完成完整项目的开发。

3.最佳实践:支撑“双模"高效运作的三个原则
要让上述两种模式顺利运转，Anthropic团队总结了三个至关重要的底层原则。这是构建高效人机协同系统所必需的思维方式。
1.原则一:建立自我验证的闭环系统
让 AI 承担一部分验证工作。成功的实践是在更求八编写功能代巩之前牛让它生成对应的测试用例(可以写在 memory 或者systemrules 中)。随后，Al的任务就变成了“通过所有测试"。这个简单的流程转变，创建了一个能自我修正的闭环，极大提升了自主模式的可靠性。
举一个简单的例子，你可以在项目中构建两个脚本 lint.sh和unittest.sh ，分别代表代码规范和单元测试。随后在 prompt或者添加一个专门的 CONTRIBUTING.md告诉 LLM 需要撰写并通过这些检查。这样简单的设置能让代码可用性高不少
2.原则二:培养精准的任务分类直觉2
高效协作的前提是做出正确的决策:何时放手，何时掌控。开发者需要培养一种直觉，能够快鐒骟摔蚪速判断一个任务是适合“Agent”模式的外围探索，还是需要“Ask"模式的核心构建。这种判断力，是区分普通使用者与高级玩家的关键。
原则三:追求工程级别的精确沟通
与 AI 的沟通应被视为一种严肃的工程行为。模糊的指令必然导致不可靠的输出。尤其在同步模式下，提示应如同 API文档般精确，明确指出要操作的文件、函数、类以及预期的行为。沟通的精度，直接决定了协作

3.原则三:追求工程级别的精确沟通
与 Al 的沟通应被视为一种严肃的工程行为。模糊的指令必然导致不可靠的输出。尤其在同步模式下，提示应如同 API文档般精确，明确指出要操作的文件、函数、类以及预期的行为。沟通的精度，直接决定了协作的效率和产出的质量。
例子:基于一个具体的 Bug Fix
反例:一个让人摸不着头脑的请求
"修复一下 Bug。"
(哪个Bug?在哪个页面?什么情况下发生的?)
这种请求只会让 LLM 困惑，可能还会乱改代码。
正例:一个可直接执行的清晰请求
【登录 Bug】 用户输入错误的用户名或密码后，页面卡死并显示为空白，无法进行任何操作。"
通过提供具体的场景、复现步骤和现象描述，我们可以帮助 LLM 一定在解决正确的问题。否则，无论 LLM 能力多强，你都觉得它无法正确帮助你。


结语:从“使用工具"到“重塑工作流”
阅读 Anthropic 内部的最佳实践，让我思考:AI 对软件开发的影响，正从单纯的“效率工具"演变为深刻的“工作流重塑”
因为现在 AI的问题不再是能写什么代码?而是“如何与 AI协同，以最高效、最可靠的方式完成整个项目?"。双模驱动的协作开发框架，以及其背后的三大原则，为我们提供了一个极具价值的 Al Coding 最佳实践。
从编程小白的角度来说，Agent模式的不断发展会抹平实现(lmplementation)的价值，你可以不断尝试创造新的idea 用agent 模式快速实现原型产品，
而从程序员的角度来说，也无需过度恐惧:掌握这种新范式，你也可以成为 10x工程师。这意味着要将自己从繁琐的编码执行中解放出来(因为在写简易代码的方向上，100x你可能都写不过1个AI)，更专注于架构设计、复杂问题分解和创造性思考(这是小白们所不擅长的)，同时区别于以前的多做代码实现，现在看来多基于 AI快速的阅读世界上最优秀的代码，提高代码品味。这或许才是 AI时代，程序员真正的核心竞争力。