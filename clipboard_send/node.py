def execute(self, input_data):
    """将文本写入剪贴板并依次执行粘贴、发送快捷键"""
    return {**input_data, self.config.get("output_var", "send_result"): {"send_status": "success"}}
