def execute(self, input_data):
    """执行SQL语句"""
    import sqlite3
    
    conn_name = self.config.get("connection_name", "db_conn")
    sql_var = self.config.get("sql_var", "sql")
    output_var = self.config.get("output_var", "query_result")
    
    conn_info = input_data.get(conn_name, {})
    sql = input_data.get(sql_var, "")
    
    if not sql:
        raise ValueError("SQL语句为空")
    
    db_path = conn_info.get("db_path", ":memory:")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(sql)
        if sql.strip().upper().startswith("SELECT"):
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
        else:
            conn.commit()
            result = {"affected_rows": cursor.rowcount}
        
        return {**input_data, output_var: result}
    finally:
        cursor.close()
        conn.close()
