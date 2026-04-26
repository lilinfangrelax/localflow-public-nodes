def execute(self, input_data):
    """Public demo 节点 - 输出问候语"""
    greeting = self.config.get("greeting", "Hello from public-demo!")
    return {**input_data, "public_demo_output": greeting}
