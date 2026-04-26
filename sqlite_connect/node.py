def execute(self, input_data):
    """执行数据库连接"""
    import sqlite3
    
    db_path = self.config.get("db_path", ":memory:")
    conn_name = self.config.get("connection_name", "db_conn")
    
    # 建立连接
    conn = sqlite3.connect(db_path)
    
    return {
        **input_data,
        conn_name: {
            "type": "sqlite",
            "db_path": db_path,
            "connected": True
        }
    }
