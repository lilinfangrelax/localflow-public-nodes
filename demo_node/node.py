def execute(self, input_data):
    """Demo 节点 - 输出问候语"""
    greeting = self.config.get("greeting", "Hello LocalFlow!")
    return {**input_data, "demo_output": greeting}
