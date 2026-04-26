def execute(self, input_data):
    """执行变量计算"""
    expression = self.config.get("expression", "0")
    output_var = self.config.get("output_var", "result")
    
    # 使用输入数据作为计算上下文
    context = {**input_data}
    result = eval(expression, {"__builtins__": {}}, context)
    
    return {**input_data, output_var: result}
