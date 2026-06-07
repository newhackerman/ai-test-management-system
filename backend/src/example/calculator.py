"""
示例模块用于测试覆盖率分析
"""

def add(a, b):
    """加法函数"""
    return a + b

def subtract(a, b):
    """减法函数"""
    return a - b

def divide(a, b):
    """除法函数"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def complex_function(x):
    """复杂函数用于测试复杂度分析"""
    if x > 10:
        if x > 20:
            if x > 30:
                return "very high"
            else:
                return "high"
        else:
            return "medium"
    else:
        return "low"

class Calculator:
    """计算器类"""
    
    def __init__(self):
        self.history = []
    
    def calculate(self, operation, a, b):
        """执行计算"""
        if operation == "add":
            result = add(a, b)
        elif operation == "subtract":
            result = subtract(a, b)
        elif operation == "divide":
            result = divide(a, b)
        else:
            raise ValueError("Unknown operation")
        
        self.history.append((operation, a, b, result))
        return result
    
    def get_history(self):
        """获取历史记录"""
        return self.history
