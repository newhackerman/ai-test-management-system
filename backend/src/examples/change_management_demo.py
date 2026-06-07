"""
需求变更管理系统演示

本演示展示了需求变更管理系统的主要功能，包括：
- 创建和管理变更请求
- 执行影响分析
- 进行风险评估
- 工作流管理
"""
import asyncio
from datetime import date, datetime
from decimal import Decimal

from models.requirement import (
    Requirement, RequirementChangeRequest, ChangeType, ChangePriority,
    RequirementStatus, Priority, BusinessValue, Complexity
)
from schemas.requirement_change import (
    ChangeRequestCreate, ImpactAnalysisRequest
)


class ChangeManagementDemo:
    """变更管理演示类"""
    
    def __init__(self):
        self.demo_data = self._create_demo_data()
    
    def _create_demo_data(self):
        """创建演示数据"""
        return {
            "requirements": [
                Requirement(
                    id=1,
                    requirement_code="REQ-AUTH-001",
                    project_id=1,
                    title="用户认证系统",
                    description="实现用户登录、注册和基础权限管理功能",
                    requirement_type="FUNCTIONAL",
                    status=RequirementStatus.IN_DEVELOPMENT,
                    priority=Priority.HIGH,
                    business_value=BusinessValue.CORE,
                    complexity=Complexity.COMPLEX,
                    estimated_effort=Decimal("15.0")
                ),
                Requirement(
                    id=2,
                    requirement_code="REQ-AUTH-002",
                    project_id=1,
                    title="权限管理模块",
                    description="管理用户角色、权限分配和访问控制",
                    requirement_type="FUNCTIONAL",
                    status=RequirementStatus.APPROVED,
                    priority=Priority.MEDIUM,
                    business_value=BusinessValue.IMPORTANT,
                    complexity=Complexity.MEDIUM,
                    estimated_effort=Decimal("8.0")
                ),
                Requirement(
                    id=3,
                    requirement_code="REQ-LOG-001",
                    project_id=1,
                    title="操作审计日志",
                    description="记录用户操作和系统事件的审计日志",
                    requirement_type="NON_FUNCTIONAL",
                    status=RequirementStatus.DRAFT,
                    priority=Priority.LOW,
                    business_value=BusinessValue.NORMAL,
                    complexity=Complexity.SIMPLE,
                    estimated_effort=Decimal("5.0")
                )
            ],
            "change_scenarios": [
                {
                    "name": "安全增强变更",
                    "requirement_id": 1,
                    "change_type": ChangeType.MODIFICATION,
                    "priority": ChangePriority.HIGH,
                    "title": "增加多因子认证支持",
                    "description": "为用户认证系统增加短信验证码和邮箱验证的多因子认证功能",
                    "reason": "提高系统安全性，满足合规要求",
                    "expected_impact": "高影响 - 涉及核心认证流程"
                },
                {
                    "name": "功能删除变更",
                    "requirement_id": 3,
                    "change_type": ChangeType.DELETION,
                    "priority": ChangePriority.MEDIUM,
                    "title": "移除审计日志功能",
                    "description": "由于存储成本考虑，移除操作审计日志功能",
                    "reason": "降低系统复杂度和存储成本",
                    "expected_impact": "中等影响 - 影响合规性"
                },
                {
                    "name": "紧急修复变更",
                    "requirement_id": 2,
                    "change_type": ChangeType.MODIFICATION,
                    "priority": ChangePriority.EMERGENCY,
                    "title": "修复权限漏洞",
                    "description": "修复权限管理模块中的安全漏洞",
                    "reason": "发现严重安全漏洞，需要紧急修复",
                    "expected_impact": "高影响 - 安全关键"
                }
            ]
        }
    
    async def run_demo(self):
        """运行完整演示"""
        print("🚀 需求变更管理系统演示开始")
        print("=" * 60)
        
        # 1. 展示系统概览
        await self._show_system_overview()
        
        # 2. 演示变更请求创建
        await self._demo_change_request_creation()
        
        # 3. 演示影响分析
        await self._demo_impact_analysis()
        
        # 4. 演示风险评估
        await self._demo_risk_assessment()
        
        # 5. 演示工作流管理
        await self._demo_workflow_management()
        
        # 6. 演示统计和报告
        await self._demo_statistics_and_reporting()
        
        print("\n✅ 需求变更管理系统演示完成")
        print("=" * 60)
    
    async def _show_system_overview(self):
        """展示系统概览"""
        print("\n📋 系统概览")
        print("-" * 30)
        
        requirements = self.demo_data["requirements"]
        print(f"📊 当前需求总数: {len(requirements)}")
        
        status_count = {}
        for req in requirements:
            status = req.status.value
            status_count[status] = status_count.get(status, 0) + 1
        
        print("📈 需求状态分布:")
        for status, count in status_count.items():
            print(f"   • {status}: {count}")
        
        print(f"\n🎯 变更场景数量: {len(self.demo_data['change_scenarios'])}")
        
        await asyncio.sleep(1)
    
    async def _demo_change_request_creation(self):
        """演示变更请求创建"""
        print("\n🆕 变更请求创建演示")
        print("-" * 30)
        
        for i, scenario in enumerate(self.demo_data["change_scenarios"], 1):
            print(f"\n场景 {i}: {scenario['name']}")
            print(f"📝 标题: {scenario['title']}")
            print(f"📄 描述: {scenario['description']}")
            print(f"🎯 原因: {scenario['reason']}")
            print(f"🔄 类型: {scenario['change_type'].value}")
            print(f"⚡ 优先级: {scenario['priority'].value}")
            print(f"📊 预期影响: {scenario['expected_impact']}")
            
            # 模拟创建变更请求
            change_request = self._create_mock_change_request(scenario, i)
            print(f"✅ 变更请求已创建: {change_request.change_request_code}")
            
            await asyncio.sleep(0.5)
    
    async def _demo_impact_analysis(self):
        """演示影响分析"""
        print("\n🔍 影响分析演示")
        print("-" * 30)
        
        scenario = self.demo_data["change_scenarios"][0]  # 使用第一个场景
        requirement = self._get_requirement_by_id(scenario["requirement_id"])
        
        print(f"📋 分析需求: {requirement.title}")
        print(f"🔄 变更类型: {scenario['change_type'].value}")
        
        # 模拟影响分析结果
        impact_result = self._simulate_impact_analysis(requirement, scenario)
        
        print(f"\n📊 影响分析结果:")
        print(f"   • 直接影响需求数: {impact_result['direct_impacts']}")
        print(f"   • 间接影响需求数: {impact_result['indirect_impacts']}")
        print(f"   • 级联深度: {impact_result['cascade_depth']}")
        print(f"   • 风险评分: {impact_result['risk_score']:.1f}/10")
        
        print(f"\n💡 主要建议:")
        for recommendation in impact_result['recommendations']:
            print(f"   • {recommendation}")
        
        await asyncio.sleep(1)
    
    async def _demo_risk_assessment(self):
        """演示风险评估"""
        print("\n⚠️ 风险评估演示")
        print("-" * 30)
        
        for scenario in self.demo_data["change_scenarios"]:
            requirement = self._get_requirement_by_id(scenario["requirement_id"])
            
            print(f"\n📋 评估需求: {requirement.title}")
            print(f"🔄 变更类型: {scenario['change_type'].value}")
            
            # 模拟风险评估
            risk_result = self._simulate_risk_assessment(requirement, scenario)
            
            print(f"📊 风险评估结果:")
            print(f"   • 识别风险数: {risk_result['risk_count']}")
            print(f"   • 整体风险级别: {risk_result['risk_level']}")
            print(f"   • 风险评分: {risk_result['risk_score']:.1f}/10")
            
            print(f"🎯 主要风险:")
            for risk in risk_result['top_risks']:
                print(f"   • {risk['category']}: {risk['description']}")
            
            await asyncio.sleep(0.5)
    
    async def _demo_workflow_management(self):
        """演示工作流管理"""
        print("\n🔄 工作流管理演示")
        print("-" * 30)
        
        scenarios = self.demo_data["change_scenarios"]
        
        # 演示不同优先级的工作流选择
        for scenario in scenarios:
            print(f"\n📋 变更: {scenario['title']}")
            print(f"⚡ 优先级: {scenario['priority'].value}")
            
            workflow_type = self._select_workflow_type(scenario)
            print(f"🔄 选择工作流: {workflow_type}")
            
            # 模拟工作流步骤
            workflow_steps = self._get_workflow_steps(workflow_type)
            print(f"📝 工作流步骤:")
            for i, step in enumerate(workflow_steps, 1):
                print(f"   {i}. {step}")
            
            await asyncio.sleep(0.5)
        
        # 演示工作流执行
        print(f"\n🎬 工作流执行演示:")
        await self._simulate_workflow_execution()
    
    async def _demo_statistics_and_reporting(self):
        """演示统计和报告"""
        print("\n📊 统计和报告演示")
        print("-" * 30)
        
        # 模拟统计数据
        stats = {
            "total_changes": 15,
            "status_distribution": {
                "SUBMITTED": 3,
                "UNDER_REVIEW": 2,
                "APPROVED": 4,
                "IMPLEMENTED": 5,
                "REJECTED": 1
            },
            "type_distribution": {
                "MODIFICATION": 8,
                "ADDITION": 4,
                "DELETION": 2,
                "CLARIFICATION": 1
            },
            "priority_distribution": {
                "EMERGENCY": 1,
                "HIGH": 4,
                "MEDIUM": 7,
                "LOW": 3
            }
        }
        
        print(f"📈 变更请求统计 (最近30天):")
        print(f"   • 总变更请求数: {stats['total_changes']}")
        
        print(f"\n📊 状态分布:")
        for status, count in stats["status_distribution"].items():
            percentage = (count / stats["total_changes"]) * 100
            print(f"   • {status}: {count} ({percentage:.1f}%)")
        
        print(f"\n🔄 类型分布:")
        for change_type, count in stats["type_distribution"].items():
            percentage = (count / stats["total_changes"]) * 100
            print(f"   • {change_type}: {count} ({percentage:.1f}%)")
        
        print(f"\n⚡ 优先级分布:")
        for priority, count in stats["priority_distribution"].items():
            percentage = (count / stats["total_changes"]) * 100
            print(f"   • {priority}: {count} ({percentage:.1f}%)")
        
        # 模拟趋势分析
        print(f"\n📈 趋势分析:")
        print(f"   • 本月变更请求比上月增长 15%")
        print(f"   • 高优先级变更占比 33%")
        print(f"   • 平均审批时间: 2.3天")
        print(f"   • 平均实施时间: 5.7天")
        
        await asyncio.sleep(1)
    
    def _get_requirement_by_id(self, req_id: int) -> Requirement:
        """根据ID获取需求"""
        for req in self.demo_data["requirements"]:
            if req.id == req_id:
                return req
        return None
    
    def _create_mock_change_request(self, scenario: dict, index: int) -> RequirementChangeRequest:
        """创建模拟变更请求"""
        return RequirementChangeRequest(
            id=index,
            requirement_id=scenario["requirement_id"],
            change_request_code=f"CR-{datetime.now().strftime('%Y%m%d')}-{index:03d}",
            title=scenario["title"],
            description=scenario["description"],
            reason=scenario["reason"],
            change_type=scenario["change_type"],
            status="SUBMITTED",
            priority=scenario["priority"],
            requestor_id=1,
            requested_date=date.today()
        )
    
    def _simulate_impact_analysis(self, requirement: Requirement, scenario: dict) -> dict:
        """模拟影响分析"""
        # 基于需求特征模拟影响
        base_impact = 1
        
        if requirement.business_value == BusinessValue.CORE:
            base_impact += 2
        if requirement.complexity in [Complexity.COMPLEX, Complexity.VERY_COMPLEX]:
            base_impact += 1
        if scenario["change_type"] == ChangeType.DELETION:
            base_impact += 2
        
        return {
            "direct_impacts": min(base_impact * 2, 8),
            "indirect_impacts": min(base_impact, 5),
            "cascade_depth": min(base_impact, 4),
            "risk_score": min(base_impact * 1.5, 10),
            "recommendations": [
                "建议进行详细的技术评审",
                "需要通知所有相关干系人",
                "建议制定回滚计划" if base_impact > 3 else "建议进行充分测试"
            ]
        }
    
    def _simulate_risk_assessment(self, requirement: Requirement, scenario: dict) -> dict:
        """模拟风险评估"""
        risk_factors = []
        risk_score = 0
        
        # 基于需求状态的风险
        if requirement.status == RequirementStatus.IN_DEVELOPMENT:
            risk_factors.append({
                "category": "开发风险",
                "description": "需求正在开发中，变更可能导致开发中断"
            })
            risk_score += 2
        
        # 基于变更类型的风险
        if scenario["change_type"] == ChangeType.DELETION:
            risk_factors.append({
                "category": "业务风险",
                "description": "删除需求可能影响业务功能完整性"
            })
            risk_score += 3
        
        # 基于业务价值的风险
        if requirement.business_value == BusinessValue.CORE:
            risk_factors.append({
                "category": "业务风险",
                "description": "核心业务需求变更可能影响系统稳定性"
            })
            risk_score += 2
        
        # 基于优先级的风险
        if scenario["priority"] == ChangePriority.EMERGENCY:
            risk_factors.append({
                "category": "时间风险",
                "description": "紧急变更可能导致质量问题"
            })
            risk_score += 1
        
        risk_level = "高" if risk_score >= 5 else "中" if risk_score >= 3 else "低"
        
        return {
            "risk_count": len(risk_factors),
            "risk_score": min(risk_score, 10),
            "risk_level": risk_level,
            "top_risks": risk_factors[:3]
        }
    
    def _select_workflow_type(self, scenario: dict) -> str:
        """选择工作流类型"""
        if scenario["change_type"] == ChangeType.DELETION:
            return "删除变更流程"
        elif scenario["priority"] in [ChangePriority.EMERGENCY, ChangePriority.HIGH]:
            return "紧急变更流程"
        else:
            return "标准变更流程"
    
    def _get_workflow_steps(self, workflow_type: str) -> list:
        """获取工作流步骤"""
        workflows = {
            "标准变更流程": [
                "提交变更请求",
                "初步评审",
                "正式审批",
                "变更实施",
                "验证完成"
            ],
            "紧急变更流程": [
                "提交紧急变更",
                "紧急审批",
                "立即实施",
                "事后验证"
            ],
            "删除变更流程": [
                "提交删除请求",
                "影响分析",
                "高级审批",
                "谨慎实施",
                "确认完成"
            ]
        }
        return workflows.get(workflow_type, [])
    
    async def _simulate_workflow_execution(self):
        """模拟工作流执行"""
        steps = [
            ("提交变更请求", "✅ 已完成"),
            ("初步评审", "🔄 进行中"),
            ("正式审批", "⏳ 等待中"),
            ("变更实施", "⏳ 等待中"),
            ("验证完成", "⏳ 等待中")
        ]
        
        print(f"📋 当前工作流状态:")
        for step, status in steps:
            print(f"   • {step}: {status}")
        
        print(f"\n👤 当前处理人: 评审员 (张三)")
        print(f"⏰ 预计完成时间: 2024-12-24 18:00")
        
        await asyncio.sleep(0.5)


async def main():
    """主函数"""
    demo = ChangeManagementDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())