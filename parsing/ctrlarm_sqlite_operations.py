

import sqlite3
import pandas as pd
import os
from datetime import datetime


class CtrlArmSQLiteDB:
    def __init__(self, database_path):
        
        self.database_path = database_path
        self.connection = None
        self.connect()

    def connect(self):
        
        try:
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
            
            self.connection = sqlite3.connect(self.database_path)
            self.connection.row_factory = sqlite3.Row
            print(f"Connected to SQLite database: {self.database_path}")
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            raise

    def disconnect(self):
        
        if self.connection:
            self.connection.close()
            print("Disconnected from SQLite database")

    def create_table(self, table_name, columns, primary_key=None):
        
        try:
            cursor = self.connection.cursor()
            
            column_definitions = []
            for col_name, col_type in columns.items():
                if primary_key and col_name == primary_key:
                    column_definitions.append(f"{col_name} {col_type} PRIMARY KEY")
                else:
                    column_definitions.append(f"{col_name} {col_type}")
            
            create_sql = f
            
            cursor.execute(create_sql)
            self.connection.commit()
            print(f"Table '{table_name}' created successfully")
            
        except sqlite3.Error as e:
            print(f"Error creating table '{table_name}': {e}")
            raise

    def create_gesture_metadata_table(self):
        
        columns = {
            'id': 'INTEGER',
            'filename': 'TEXT',
            'filepath': 'TEXT',
            'gesture_type': 'TEXT',
            'gesture_category': 'TEXT',
            'date': 'TEXT',
            'time': 'TEXT',
            'timestamp': 'TEXT',
            'duration_ms': 'REAL',
            'sample_count': 'INTEGER',
            'sampling_rate': 'REAL',
            'data_quality_score': 'REAL',
            'emg1_left_mean': 'REAL',
            'emg1_left_std': 'REAL',
            'emg1_left_min': 'REAL',
            'emg1_left_max': 'REAL',
            'emg1_left_range': 'REAL',
            'emg1_left_median': 'REAL',
            'emg1_left_q25': 'REAL',
            'emg1_left_q75': 'REAL',
            'emg2_right_mean': 'REAL',
            'emg2_right_std': 'REAL',
            'emg2_right_min': 'REAL',
            'emg2_right_max': 'REAL',
            'emg2_right_range': 'REAL',
            'emg2_right_median': 'REAL',
            'emg2_right_q25': 'REAL',
            'emg2_right_q75': 'REAL',
            'accel_x_mean': 'REAL',
            'accel_x_std': 'REAL',
            'accel_x_min': 'REAL',
            'accel_x_max': 'REAL',
            'accel_x_range': 'REAL',
            'accel_x_median': 'REAL',
            'accel_x_q25': 'REAL',
            'accel_x_q75': 'REAL',
            'accel_y_mean': 'REAL',
            'accel_y_std': 'REAL',
            'accel_y_min': 'REAL',
            'accel_y_max': 'REAL',
            'accel_y_range': 'REAL',
            'accel_y_median': 'REAL',
            'accel_y_q25': 'REAL',
            'accel_y_q75': 'REAL',
            'accel_z_mean': 'REAL',
            'accel_z_std': 'REAL',
            'accel_z_min': 'REAL',
            'accel_z_max': 'REAL',
            'accel_z_range': 'REAL',
            'accel_z_median': 'REAL',
            'accel_z_q25': 'REAL',
            'accel_z_q75': 'REAL',
            'gyro_x_mean': 'REAL',
            'gyro_x_std': 'REAL',
            'gyro_x_min': 'REAL',
            'gyro_x_max': 'REAL',
            'gyro_x_range': 'REAL',
            'gyro_x_median': 'REAL',
            'gyro_x_q25': 'REAL',
            'gyro_x_q75': 'REAL',
            'gyro_y_mean': 'REAL',
            'gyro_y_std': 'REAL',
            'gyro_y_min': 'REAL',
            'gyro_y_max': 'REAL',
            'gyro_y_range': 'REAL',
            'gyro_y_median': 'REAL',
            'gyro_y_q25': 'REAL',
            'gyro_y_q75': 'REAL',
            'gyro_z_mean': 'REAL',
            'gyro_z_std': 'REAL',
            'gyro_z_min': 'REAL',
            'gyro_z_max': 'REAL',
            'gyro_z_range': 'REAL',
            'gyro_z_median': 'REAL',
            'gyro_z_q25': 'REAL',
            'gyro_z_q75': 'REAL',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP'
        }
        
        self.create_table('gesture_metadata', columns, primary_key='id')

    def insert_record(self, table_name, data):
        
        try:
            cursor = self.connection.cursor()
            
            now = datetime.now().isoformat()
            data['created_at'] = now
            data['updated_at'] = now
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data.keys()])
            insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            
            cursor.execute(insert_sql, list(data.values()))
            self.connection.commit()
            
            return cursor.lastrowid
            
        except sqlite3.Error as e:
            print(f"Error inserting record into '{table_name}': {e}")
            raise

    def insert_records(self, table_name, records):
        
        try:
            cursor = self.connection.cursor()
            
            if not records:
                return 0
            
            now = datetime.now().isoformat()
            for record in records:
                record['created_at'] = now
                record['updated_at'] = now
            
            columns = ', '.join(records[0].keys())
            placeholders = ', '.join(['?' for _ in records[0].keys()])
            insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            
            data_to_insert = [list(record.values()) for record in records]
            
            cursor.executemany(insert_sql, data_to_insert)
            self.connection.commit()
            
            return len(records)
            
        except sqlite3.Error as e:
            print(f"Error inserting records into '{table_name}': {e}")
            raise

    def read_records(self, table_name, columns=None, where_clause=None, limit=None):
        
        try:
            cursor = self.connection.cursor()
            
            if columns:
                select_columns = ', '.join(columns)
            else:
                select_columns = '*'
            
            sql = f"SELECT {select_columns} FROM {table_name}"
            
            if where_clause:
                sql += f" WHERE {where_clause}"
            
            if limit:
                sql += f" LIMIT {limit}"
            
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            if rows:
                df = pd.DataFrame([dict(row) for row in rows])
                return df
            else:
                return pd.DataFrame()
                
        except sqlite3.Error as e:
            print(f"Error reading records from '{table_name}': {e}")
            raise

    def update_record(self, table_name, data, where_clause):
        
        try:
            cursor = self.connection.cursor()
            
            data['updated_at'] = datetime.now().isoformat()
            
            set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
            update_sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
            
            cursor.execute(update_sql, list(data.values()))
            self.connection.commit()
            
            return cursor.rowcount
            
        except sqlite3.Error as e:
            print(f"Error updating records in '{table_name}': {e}")
            raise

    def delete_records(self, table_name, where_clause):
        
        try:
            cursor = self.connection.cursor()
            
            delete_sql = f"DELETE FROM {table_name} WHERE {where_clause}"
            cursor.execute(delete_sql)
            self.connection.commit()
            
            return cursor.rowcount
            
        except sqlite3.Error as e:
            print(f"Error deleting records from '{table_name}': {e}")
            raise

    def create_sqlite_records_from_dataframe(self, table_name, df):
        
        try:
            records = df.to_dict('records')
            
            return self.insert_records(table_name, records)
            
        except Exception as e:
            print(f"Error creating records from DataFrame: {e}")
            raise

    def get_table_info(self, table_name):
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            return cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f"Error getting table info for '{table_name}': {e}")
            raise

    def get_table_names(self):
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            print(f"Error getting table names: {e}")
            raise

    def execute_custom_query(self, query, params=None):
        
        try:
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            self.connection.commit()
            return cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f"Error executing custom query: {e}")
            raise
