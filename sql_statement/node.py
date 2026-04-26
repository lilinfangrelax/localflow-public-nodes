def execute(self, input_data):
    """生成SQL语句"""
    sql_template = self.config.get("sql", "")
    output_var = self.config.get("output_var", "sql")
    
    # 使用输入数据格式化SQL
    sql = sql_template.format(**input_data)
    
    return {**input_data, output_var: sql}
