from __future__ import annotations

from .domain.models import DecisionRule, StoryNode
from .domain.route_planner import build_route_plan


DEMO_PLAN_ID = "czlife-mvp"
DEMO_VERSION = 1


def demo_nodes() -> list[StoryNode]:
    return [
        StoryNode(
            "N11", 11, "决定创办 Binance", "2017", "待核地点",
            "Binance 官方 About 页面将 Binance 列为 2017 年成立并将 CZ 列为创始人。",
            ("https://www.binance.com/en/about",),
            "这是创业项目从想法进入现实的节点。",
            "用紧迫的创业现场承载虚构对白，不补写未经证实的团队细节。",
        ),
        StoryNode(
            "N12", 12, "发行 BNB 并完成 ICO", "2017-07", "待核地点",
            "Binance Academy 的 BNB 资料将 BNB 发行置于 2017 年 7 月 ICO。",
            ("https://academy.binance.com/en/articles/what-is-bnb",),
            "代币发行让平台计划有了可持续的资源。",
            "ICO 的具体数字只来自原始文件；其余临场选择属于小说。",
        ),
        StoryNode(
            "N16", 16, "Binance Chain 主网上线", "2019", "Binance Chain 生态",
            "官方 BNB Chain 资料确认 Binance Chain 与 BNB 生态的演进。",
            ("https://academy.binance.com/en/articles/what-is-bnb-chain",),
            "交易平台开始向链上基础设施扩张。",
            "技术讨论可以文学化，但不虚构未公开的团队决策记录。",
        ),
        StoryNode(
            "N17", 17, "BNB 从 ERC-20 迁移到 Binance Chain", "2019", "Binance Chain / Ethereum",
            "官方 BNB 历史资料支持早期 ERC-20 形态及后续链上迁移。",
            ("https://academy.binance.com/en/articles/what-is-bnb-chain",),
            "迁移把一次资产发行变成持续运行的生态。",
            "迁移批次和规则以原始公告为边界，虚构内容只描述人物体验。",
        ),
        StoryNode(
            "N19", 19, "BNB Smart Chain 主网上线", "2020-09", "BNB Smart Chain 生态",
            "官方 BNB Chain 介绍记载 BNB Smart Chain 的发展脉络。",
            ("https://academy.binance.com/en/articles/what-is-bnb-chain",),
            "另一条链让生态开始承载更多应用。",
            "不把技术路线改写成单人临时决定。",
        ),
        StoryNode(
            "N20", 20, "宣布拟收购 FTX，随后撤回", "2022-11", "线上 / 全球交易市场",
            "CZ 的公开声明和 Binance 当时公告支持拟收购与撤回的事件顺序。",
            ("https://twitter.com/cz_binance",),
            "这是高风险公开决策节点，事实和评论必须分开。",
            "不把 FTX 后续复杂因果归于单一人物。",
        ),
        StoryNode(
            "N21", 21, "认罪并辞任 Binance CEO", "2023-11-21", "美国司法管辖范围",
            "美国司法部公告称 CZ 对违反银行保密法的指控认罪并辞任 CEO。",
            ("https://www.justice.gov/usao-wdwa/pr/binance-founder-and-ceo-pleads-guilty-charges-violating-us-anti-money",),
            "公开身份和公司治理在这里发生断裂。",
            "必须区分司法文件事实与小说中的道德评价。",
        ),
        StoryNode(
            "N22", 22, "被判处四个月监禁", "2024-04-30", "美国联邦法院",
            "美国司法部公告称 CZ 因违反银行保密法被判处四个月监禁。",
            ("https://www.justice.gov/usao-wdwa/pr/binance-founder-and-ceo-sentenced-four-months-prison",),
            "故事的现实锚点抵达司法后果，之后的首富结局属于平行世界。",
            "不由判决日期推断服刑地点、释放日期或后续事实。",
        ),
    ]


def demo_rules() -> list[DecisionRule]:
    node_ids = [node.node_id for node in demo_nodes()]
    thresholds = [25, 35, 45, 55, 65, 72, 80]
    return [
        DecisionRule(
            rule_id=f"rule-{from_id}-{to_id}",
            from_node_id=from_id,
            to_node_id=to_id,
            success_threshold=threshold,
            memory_effect=8,
        )
        for from_id, to_id, threshold in zip(node_ids, node_ids[1:], thresholds)
    ]


def build_demo_plan():
    return build_route_plan(
        plan_id=DEMO_PLAN_ID,
        version=DEMO_VERSION,
        title="我的模拟首富路",
        ticker="CZ 人生",
        nodes=demo_nodes(),
        rules=demo_rules(),
        seed=1,
        max_lives=8,
    )

