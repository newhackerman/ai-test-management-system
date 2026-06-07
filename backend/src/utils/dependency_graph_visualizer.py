"""
需求依赖关系图可视化工具

本模块提供需求依赖关系的可视化功能，包括：
- 生成Mermaid图表
- 生成DOT图表
- 生成JSON格式的图数据
- 依赖路径分析
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models.requirement import Requirement, RequirementDependency, DependencyType


class GraphFormat(Enum):
    """图表格式枚举"""
    MERMAID = "mermaid"
    DOT = "dot"
    JSON = "json"


@dataclass
class GraphNode:
    """图节点"""
    id: int
    title: str
    status: str
    priority: str
    type: str = "requirement"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "type": self.type
        }


@dataclass
class GraphEdge:
    """图边"""
    source: int
    target: int
    type: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "description": self.description
        }


class DependencyGraphVisualizer:
    """依赖关系图可视化器"""
    
    def __init__(self):
        """初始化可视化器"""
        self.dependency_type_colors = {
            "DEPENDS_ON": "#FF6B6B",
            "BLOCKS": "#4ECDC4", 
            "RELATES_TO": "#45B7D1",
            "CONFLICTS_WITH": "#FFA07A",
            "DUPLICATES": "#98D8C8",
            "REPLACES": "#F7DC6F"
        }
        
        self.status_colors = {
            "DRAFT": "#E8E8E8",
            "PENDING_REVIEW": "#FFE4B5",
            "REVIEWING": "#DDA0DD",
            "NEEDS_REVISION": "#F0E68C",
            "APPROVED": "#90EE90",
            "IN_DEVELOPMENT": "#87CEEB",
            "PAUSED": "#D3D3D3",
            "TESTING": "#DEB887",
            "TEST_FAILED": "#FA8072",
            "COMPLETED": "#98FB98",
            "DEPLOYED": "#00FA9A",
            "CLOSED": "#B0C4DE",
            "CANCELLED": "#C0C0C0"
        }
        
        self.priority_shapes = {
            "CRITICAL": "diamond",
            "HIGH": "rect",
            "MEDIUM": "circle",
            "LOW": "ellipse",
            "OPTIONAL": "hexagon"
        }
    
    def generate_graph(
        self,
        requirements: List[Requirement],
        dependencies: List[RequirementDependency],
        format_type: GraphFormat = GraphFormat.JSON,
        include_isolated: bool = True,
        max_nodes: int = 100
    ) -> str:
        """
        生成依赖关系图
        
        Args:
            requirements: 需求列表
            dependencies: 依赖关系列表
            format_type: 图表格式
            include_isolated: 是否包含孤立节点
            max_nodes: 最大节点数
            
        Returns:
            图表字符串
        """
        # 构建节点和边
        nodes, edges = self._build_graph_data(
            requirements, dependencies, include_isolated, max_nodes
        )
        
        # 根据格式生成图表
        if format_type == GraphFormat.MERMAID:
            return self._generate_mermaid_graph(nodes, edges)
        elif format_type == GraphFormat.DOT:
            return self._generate_dot_graph(nodes, edges)
        else:  # JSON
            return self._generate_json_graph(nodes, edges)
    
    def _build_graph_data(
        self,
        requirements: List[Requirement],
        dependencies: List[RequirementDependency],
        include_isolated: bool,
        max_nodes: int
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """构建图数据"""
        # 创建需求ID到需求对象的映射
        req_map = {req.id: req for req in requirements}
        
        # 获取有依赖关系的需求ID
        connected_req_ids = set()
        for dep in dependencies:
            connected_req_ids.add(dep.source_requirement_id)
            connected_req_ids.add(dep.target_requirement_id)
        
        # 构建节点
        nodes = []
        included_req_ids = set()
        
        # 优先包含有依赖关系的需求
        for req_id in connected_req_ids:
            if len(nodes) >= max_nodes:
                break
            if req_id in req_map:
                req = req_map[req_id]
                nodes.append(self._create_graph_node(req))
                included_req_ids.add(req_id)
        
        # 如果包含孤立节点，添加剩余需求
        if include_isolated:
            for req in requirements:
                if len(nodes) >= max_nodes:
                    break
                if req.id not in included_req_ids:
                    nodes.append(self._create_graph_node(req))
                    included_req_ids.add(req.id)
        
        # 构建边
        edges = []
        for dep in dependencies:
            if (dep.source_requirement_id in included_req_ids and 
                dep.target_requirement_id in included_req_ids):
                edges.append(GraphEdge(
                    source=dep.source_requirement_id,
                    target=dep.target_requirement_id,
                    type=dep.dependency_type.value,
                    description=dep.description
                ))
        
        return nodes, edges
    
    def _create_graph_node(self, requirement: Requirement) -> GraphNode:
        """创建图节点"""
        return GraphNode(
            id=requirement.id,
            title=requirement.title,
            status=requirement.status.value if requirement.status else "DRAFT",
            priority=requirement.priority.value if requirement.priority else "MEDIUM"
        )
    
    def _generate_mermaid_graph(self, nodes: List[GraphNode], edges: List[GraphEdge]) -> str:
        """生成Mermaid图表"""
        lines = ["graph TD"]
        
        # 添加节点定义
        for node in nodes:
            shape = self.priority_shapes.get(node.priority, "rect")
            color = self.status_colors.get(node.status, "#E8E8E8")
            
            if shape == "diamond":
                node_def = f'    {node.id}{{{node.title}}}'
            elif shape == "circle":
                node_def = f'    {node.id}(({node.title}))'
            elif shape == "ellipse":
                node_def = f'    {node.id}([{node.title}])'
            elif shape == "hexagon":
                node_def = f'    {node.id}{{{{{node.title}}}}}'
            else:  # rect
                node_def = f'    {node.id}[{node.title}]'
            
            lines.append(node_def)
            lines.append(f'    {node.id} --> {node.id}')
            lines.append(f'    style {node.id} fill:{color}')
        
        # 添加边定义
        for edge in edges:
            color = self.dependency_type_colors.get(edge.type, "#000000")
            arrow_style = self._get_mermaid_arrow_style(edge.type)
            
            if edge.description:
                edge_def = f'    {edge.source} {arrow_style} {edge.target}'
                lines.append(f'{edge_def} : {edge.description}')
            else:
                lines.append(f'    {edge.source} {arrow_style} {edge.target}')
            
            lines.append(f'    linkStyle {len(lines)-1} stroke:{color}')
        
        return '\n'.join(lines)
    
    def _generate_dot_graph(self, nodes: List[GraphNode], edges: List[GraphEdge]) -> str:
        """生成DOT图表"""
        lines = ["digraph DependencyGraph {"]
        lines.append("    rankdir=TB;")
        lines.append("    node [fontname=\"Arial\"];")
        lines.append("    edge [fontname=\"Arial\"];")
        
        # 添加节点定义
        for node in nodes:
            shape = self.priority_shapes.get(node.priority, "box")
            color = self.status_colors.get(node.status, "#E8E8E8")
            
            lines.append(f'    {node.id} [label="{node.title}\\n({node.status})", '
                        f'shape={shape}, fillcolor="{color}", style=filled];')
        
        # 添加边定义
        for edge in edges:
            color = self.dependency_type_colors.get(edge.type, "#000000")
            style = self._get_dot_edge_style(edge.type)
            
            if edge.description:
                lines.append(f'    {edge.source} -> {edge.target} '
                           f'[label="{edge.type}\\n{edge.description}", '
                           f'color="{color}", style={style}];')
            else:
                lines.append(f'    {edge.source} -> {edge.target} '
                           f'[label="{edge.type}", color="{color}", style={style}];')
        
        lines.append("}")
        return '\n'.join(lines)
    
    def _generate_json_graph(self, nodes: List[GraphNode], edges: List[GraphEdge]) -> str:
        """生成JSON图表"""
        import json
        
        graph_data = {
            "nodes": [node.to_dict() for node in nodes],
            "edges": [edge.to_dict() for edge in edges],
            "metadata": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "dependency_types": list(set(edge.type for edge in edges)),
                "status_distribution": self._get_status_distribution(nodes),
                "priority_distribution": self._get_priority_distribution(nodes)
            }
        }
        
        return json.dumps(graph_data, indent=2, ensure_ascii=False)
    
    def _get_mermaid_arrow_style(self, dependency_type: str) -> str:
        """获取Mermaid箭头样式"""
        styles = {
            "DEPENDS_ON": "-->",
            "BLOCKS": "-.->",
            "RELATES_TO": "---",
            "CONFLICTS_WITH": "==>",
            "DUPLICATES": "~~>",
            "REPLACES": "==>"
        }
        return styles.get(dependency_type, "-->")
    
    def _get_dot_edge_style(self, dependency_type: str) -> str:
        """获取DOT边样式"""
        styles = {
            "DEPENDS_ON": "solid",
            "BLOCKS": "dashed",
            "RELATES_TO": "dotted",
            "CONFLICTS_WITH": "bold",
            "DUPLICATES": "dashed",
            "REPLACES": "bold"
        }
        return styles.get(dependency_type, "solid")
    
    def _get_status_distribution(self, nodes: List[GraphNode]) -> Dict[str, int]:
        """获取状态分布"""
        distribution = {}
        for node in nodes:
            distribution[node.status] = distribution.get(node.status, 0) + 1
        return distribution
    
    def _get_priority_distribution(self, nodes: List[GraphNode]) -> Dict[str, int]:
        """获取优先级分布"""
        distribution = {}
        for node in nodes:
            distribution[node.priority] = distribution.get(node.priority, 0) + 1
        return distribution
    
    def find_critical_path(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        start_node_id: int,
        end_node_id: int
    ) -> List[int]:
        """
        查找关键路径
        
        Args:
            nodes: 节点列表
            edges: 边列表
            start_node_id: 起始节点ID
            end_node_id: 结束节点ID
            
        Returns:
            关键路径节点ID列表
        """
        # 构建邻接表
        graph = {}
        for node in nodes:
            graph[node.id] = []
        
        for edge in edges:
            if edge.type in ["DEPENDS_ON", "BLOCKS"]:  # 只考虑强依赖关系
                graph[edge.source].append(edge.target)
        
        # 使用DFS查找路径
        def dfs(current: int, target: int, path: List[int], visited: Set[int]) -> List[int]:
            if current == target:
                return path + [current]
            
            if current in visited:
                return []
            
            visited.add(current)
            
            for neighbor in graph.get(current, []):
                result = dfs(neighbor, target, path + [current], visited.copy())
                if result:
                    return result
            
            return []
        
        return dfs(start_node_id, end_node_id, [], set())
    
    def detect_cycles(self, nodes: List[GraphNode], edges: List[GraphEdge]) -> List[List[int]]:
        """
        检测循环依赖
        
        Args:
            nodes: 节点列表
            edges: 边列表
            
        Returns:
            循环路径列表
        """
        # 构建邻接表
        graph = {}
        for node in nodes:
            graph[node.id] = []
        
        for edge in edges:
            graph[edge.source].append(edge.target)
        
        # 使用DFS检测循环
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: int, path: List[int]):
            if node in rec_stack:
                # 找到循环
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [node])
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def calculate_node_metrics(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> Dict[int, Dict[str, Any]]:
        """
        计算节点指标
        
        Args:
            nodes: 节点列表
            edges: 边列表
            
        Returns:
            节点指标字典
        """
        metrics = {}
        
        # 初始化指标
        for node in nodes:
            metrics[node.id] = {
                "in_degree": 0,
                "out_degree": 0,
                "centrality": 0.0,
                "is_critical": False,
                "dependency_depth": 0
            }
        
        # 计算入度和出度
        for edge in edges:
            if edge.source in metrics:
                metrics[edge.source]["out_degree"] += 1
            if edge.target in metrics:
                metrics[edge.target]["in_degree"] += 1
        
        # 计算中心性（简单的度中心性）
        max_degree = max(
            metrics[node_id]["in_degree"] + metrics[node_id]["out_degree"]
            for node_id in metrics
        ) if metrics else 1
        
        for node_id in metrics:
            total_degree = metrics[node_id]["in_degree"] + metrics[node_id]["out_degree"]
            metrics[node_id]["centrality"] = total_degree / max_degree if max_degree > 0 else 0
        
        # 标记关键节点（高度连接的节点）
        avg_centrality = sum(m["centrality"] for m in metrics.values()) / len(metrics) if metrics else 0
        for node_id in metrics:
            metrics[node_id]["is_critical"] = metrics[node_id]["centrality"] > avg_centrality * 1.5
        
        return metrics