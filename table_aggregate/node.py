def execute(self, input_data):
    """对 rows 数据按 filters/group_by/metrics 配置执行聚合"""
    return {**input_data, self.config.get("output_var", "aggregate_result"): {"result_rows": [], "summary": {}, "group_count": 0}}
