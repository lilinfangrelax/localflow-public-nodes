def execute(self, input_data):
    """执行变量赋值"""
    var_name = self.config.get("variable_name", "result")
    value = self.config.get("value", "")
    value_type = self.config.get("value_type", "str")
    
    # 类型转换
    if value_type == "int":
        value = int(value)
    elif value_type == "float":
        value = float(value)
    elif value_type == "bool":
        value = value.lower() in ("true", "1", "yes")
    elif value_type == "json":
        import json
        value = json.loads(value)
    
    return {var_name: value}
