import sys
import os
import socket
import threading
import json
import datetime
import sqlite3
import random
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 获取本机IP地址
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# 数据库管理类
class ChatDatabase:
    def __init__(self):
        self.db_name = "chat_history.db"
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS connections
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT,
                      ip TEXT,
                      port INTEGER,
                      last_active TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      connection_id INTEGER,
                      sender TEXT,
                      message TEXT,
                      timestamp TEXT,
                      file_path TEXT)''')
        conn.commit()
        conn.close()
    
    def add_connection(self, name, ip, port):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("INSERT INTO connections (name, ip, port, last_active) VALUES (?, ?, ?, ?)",
                 (name, ip, port, datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return c.lastrowid
    
    def get_connections(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("SELECT id, name, ip, port, last_active FROM connections ORDER BY last_active DESC")
        connections = c.fetchall()
        conn.close()
        return connections
    
    def get_connection_by_id(self, conn_id):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("SELECT id, name, ip, port, last_active FROM connections WHERE id = ?", (conn_id,))
        connection = c.fetchone()
        conn.close()
        return connection
    
    def save_message(self, connection_id, sender, message, file_path=None):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        c.execute("INSERT INTO messages (connection_id, sender, message, timestamp, file_path) VALUES (?, ?, ?, ?, ?)",
                 (connection_id, sender, message, timestamp, file_path))
        c.execute("UPDATE connections SET last_active = ? WHERE id = ?", (timestamp, connection_id))
        conn.commit()
        conn.close()
    
    def get_messages(self, connection_id):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("SELECT sender, message, timestamp, file_path FROM messages WHERE connection_id = ? ORDER BY timestamp", (connection_id,))
        messages = c.fetchall()
        conn.close()
        return messages
    
    def export_chat(self, connection_id, file_path):
        messages = self.get_messages(connection_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("聊天记录导出\n")
            f.write("=" * 50 + "\n")
            for msg in messages:
                sender, message, timestamp, file_path = msg
                dt = datetime.datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                if file_path:
                    f.write(f"[{time_str}] {sender}: [文件] {os.path.basename(file_path)}\n")
                else:
                    f.write(f"[{time_str}] {sender}: {message}\n")

# Metro风格按钮
class MetroButton(QPushButton):
    def __init__(self, text, icon=None, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                text-align: left;
                padding: 10px 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
        """)
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(24, 24))

# 连接列表项
class ConnectionItem(QListWidgetItem):
    def __init__(self, conn_id, name, ip, port, last_active, parent=None):
        super().__init__(parent)
        self.conn_id = conn_id
        self.name = name
        self.ip = ip
        self.port = port
        self.last_active = last_active
        
        dt = datetime.datetime.fromisoformat(last_active)
        time_str = dt.strftime("%m-%d %H:%M")
        self.setText(f"{name}\n{ip}:{port}  {time_str}")
        self.setSizeHint(QSize(200, 60))
        self.setFont(QFont("Segoe UI", 10))
        self.setBackground(QColor(240, 240, 240))

# 主窗口类
class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MetroChat - P2P 聊天")
        self.setGeometry(100, 100, 1000, 700)
        
        # 初始化数据库
        self.db = ChatDatabase()
        
        # 设置Metro风格
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
                font-family: Segoe UI;
            }
            QSplitter::handle {
                background-color: #E0E0E0;
                width: 1px;
            }
            QListWidget {
                background-color: white;
                border: none;
                font-size: 12px;
            }
            QListWidget::item:selected {
                background-color: #E5F1FB;
                color: black;
                border-left: 3px solid #0078D7;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        
        # 创建主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧连接面板
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 连接列表标题
        title_label = QLabel("连接列表")
        title_label.setStyleSheet("""
            QLabel {
                background-color: #0078D7;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_label)
        
        # 连接列表
        self.connection_list = QListWidget()
        self.connection_list.setStyleSheet("border: none;")
        self.connection_list.itemClicked.connect(self.on_connection_selected)
        left_layout.addWidget(self.connection_list, 1)
        
        # 底部按钮区域
        button_panel = QWidget()
        button_panel.setStyleSheet("background-color: #F0F0F0;")
        button_layout = QVBoxLayout(button_panel)
        button_layout.setContentsMargins(10, 10, 10, 10)
        
        self.new_conn_btn = MetroButton("  新建连接", QIcon.fromTheme("list-add"))
        self.new_conn_btn.clicked.connect(self.show_new_connection_dialog)
        button_layout.addWidget(self.new_conn_btn)
        
        self.connect_btn = MetroButton("  连接")
        self.connect_btn.clicked.connect(self.connect_to_selected)
        button_layout.addWidget(self.connect_btn)
        
        export_btn = MetroButton("  导出聊天记录", QIcon.fromTheme("document-save"))
        export_btn.clicked.connect(self.export_chat_history)
        button_layout.addWidget(export_btn)
        
        left_layout.addWidget(button_panel)
        
        # 右侧聊天面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        
        # 状态栏
        status_bar = QWidget()
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(5, 5, 5, 5)
        
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 12px; color: #606060;")
        status_layout.addWidget(self.status_label)
        
        self.ip_label = QLabel()
        self.ip_label.setStyleSheet("font-size: 12px; color: #606060;")
        status_layout.addWidget(self.ip_label)
        
        self.port_label = QLabel()
        self.port_label.setStyleSheet("font-size: 12px; color: #606060; font-weight: bold;")
        status_layout.addWidget(self.port_label)
        
        right_layout.addWidget(status_bar)
        
        # 聊天显示区域
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("border: 1px solid #E0E0E0; border-radius: 4px;")
        right_layout.addWidget(self.chat_display, 1)
        
        # 消息输入区域
        input_panel = QWidget()
        input_layout = QVBoxLayout(input_panel)
        
        # 输入框和按钮
        input_buttons_layout = QHBoxLayout()
        
        self.file_btn = QPushButton("📎")
        self.file_btn.setFixedSize(40, 40)
        self.file_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        self.file_btn.clicked.connect(self.attach_file)
        input_buttons_layout.addWidget(self.file_btn)
        
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("输入消息...")
        self.message_input.setMaximumHeight(100)
        self.message_input.setStyleSheet("border: 1px solid #E0E0E0; border-radius: 4px; padding: 5px;")
        input_buttons_layout.addWidget(self.message_input, 1)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(80, 40)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:disabled {
                background-color: #A0A0A0;
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_buttons_layout.addWidget(self.send_btn)
        
        input_layout.addLayout(input_buttons_layout)
        
        # 文件信息显示
        self.file_info_label = QLabel()
        self.file_info_label.setStyleSheet("color: #606060; font-size: 12px;")
        self.file_info_label.setVisible(False)
        input_layout.addWidget(self.file_info_label)
        
        right_layout.addWidget(input_panel)
        
        # 添加左右面板到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)
        
        # 初始化网络变量
        self.server_socket = None
        self.client_socket = None
        self.connection_thread = None
        self.listening = False
        self.current_file = None
        self.current_connection = None
        
        # 获取并显示本机信息
        self.local_ip = get_local_ip()
        self.ip_label.setText(f"本机IP: {self.local_ip}")
        
        # 自动选择并监听端口
        self.listen_port = self.find_available_port()
        self.start_listening(self.listen_port)
        self.port_label.setText(f"监听端口: {self.listen_port}")
        self.status_label.setText("状态: 正在监听")
        
        # 加载连接列表
        self.load_connections()
    
    def find_available_port(self):
        """自动寻找可用端口"""
        for _ in range(10):
            try:
                port = random.randint(10000, 20000)
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.bind(('', port))
                test_socket.close()
                return port
            except:
                continue
        return 9090
    
    def load_connections(self):
        self.connection_list.clear()
        connections = self.db.get_connections()
        for conn in connections:
            conn_id, name, ip, port, last_active = conn
            item = ConnectionItem(conn_id, name, ip, port, last_active)
            self.connection_list.addItem(item)
    
    def start_listening(self, port):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', port))
            self.server_socket.listen(5)
            self.listening = True
            
            # 启动监听线程
            self.connection_thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.connection_thread.start()
            
            self.show_system_message(f"正在监听端口 {port}...")
        except Exception as e:
            self.status_label.setText("状态: 监听失败")
            self.show_system_message(f"监听失败: {str(e)}")
    
    def accept_connections(self):
        while self.listening:
            try:
                client_socket, addr = self.server_socket.accept()
                ip, port = addr
                
                # 更新状态
                self.status_label.setText(f"状态: 已连接 {ip}:{port}")
                
                # 检查是否已有该连接
                existing = False
                conn_id = None
                for i in range(self.connection_list.count()):
                    item = self.connection_list.item(i)
                    if item.ip == ip:
                        conn_id = item.conn_id
                        existing = True
                        break
                
                if not existing:
                    # 创建新连接
                    conn_id = self.db.add_connection(f"{ip}:{port}", ip, port)
                    item = ConnectionItem(conn_id, f"{ip}:{port}", ip, port, datetime.datetime.now().isoformat())
                    self.connection_list.addItem(item)
                
                self.current_connection = conn_id
                self.client_socket = client_socket
                self.show_system_message(f"{ip}:{port} 已连接到本机")
                
                # 启动接收线程
                threading.Thread(target=self.receive_messages, args=(client_socket,), daemon=True).start()
            except:
                if self.listening:
                    self.status_label.setText("状态: 监听已停止")
                break
    
    def connect_to_selected(self):
        """连接到选中的联系人"""
        selected_item = self.connection_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "未选择连接", "请先在连接列表中选择一个连接")
            return
            
        # 获取连接信息
        conn_id = selected_item.conn_id
        connection = self.db.get_connection_by_id(conn_id)
        if not connection:
            QMessageBox.warning(self, "连接错误", "无法获取连接信息")
            return
            
        _, name, ip, port, _ = connection
        
        # 关闭现有连接（如果有）
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        try:
            # 创建新的socket连接
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((ip, port))
            
            # 更新状态
            self.status_label.setText(f"状态: 已连接到 {ip}:{port}")
            self.show_system_message(f"已连接到 {ip}:{port}")
            
            # 设置当前连接
            self.current_connection = conn_id
            
            # 启动接收线程
            threading.Thread(target=self.receive_messages, args=(self.client_socket,), daemon=True).start()
            
            # 加载聊天记录
            self.chat_display.clear()
            messages = self.db.get_messages(self.current_connection)
            for msg in messages:
                sender, message, timestamp, file_path = msg
                self.show_message(sender, message, file_path)
                
        except Exception as e:
            self.status_label.setText("状态: 连接失败")
            self.show_system_message(f"连接失败: {str(e)}")
    
    def receive_messages(self, sock):
        while True:
            try:
                data = sock.recv(4096).decode('utf-8')
                if not data:
                    self.status_label.setText("状态: 连接已断开")
                    break
                
                # 解析消息
                try:
                    message = json.loads(data)
                    if message['type'] == 'text':
                        self.db.save_message(self.current_connection, "对方", message['content'])
                        self.show_message("对方", message['content'])
                    elif message['type'] == 'file':
                        file_name = message['file_name']
                        file_size = int(message['file_size'])
                        self.db.save_message(self.current_connection, "对方", f"[文件] {file_name}", file_name)
                        self.show_message("对方", f"[文件] {file_name}")
                except json.JSONDecodeError:
                    self.show_system_message(f"收到消息: {data}")
            except Exception as e:
                self.show_system_message(f"接收错误: {str(e)}")
                self.status_label.setText("状态: 连接错误")
                break
    
    def show_new_connection_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("新建连接")
        dialog.setFixedSize(300, 200)
        
        layout = QVBoxLayout(dialog)
        
        form_layout = QFormLayout()
        
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("连接名称")
        form_layout.addRow("名称:", name_edit)
        
        ip_edit = QLineEdit()
        ip_edit.setPlaceholderText("IP地址")
        form_layout.addRow("IP地址:", ip_edit)
        
        port_edit = QLineEdit()
        port_edit.setPlaceholderText("端口号")
        form_layout.addRow("端口号:", port_edit)
        
        # 添加提示信息
        info_label = QLabel(f"您的信息:\nIP: {self.local_ip}\n端口: {self.listen_port}")
        info_label.setStyleSheet("font-size: 12px; color: #0078D7;")
        form_layout.addRow(info_label)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text().strip()
            ip = ip_edit.text().strip()
            port = port_edit.text().strip()
            
            if not name or not ip or not port:
                QMessageBox.warning(self, "输入错误", "请填写所有字段")
                return
                
            try:
                port = int(port)
            except ValueError:
                QMessageBox.warning(self, "输入错误", "端口号必须是数字")
                return
                
            # 添加到数据库
            conn_id = self.db.add_connection(name, ip, port)
            
            # 添加到连接列表
            item = ConnectionItem(conn_id, name, ip, port, datetime.datetime.now().isoformat())
            self.connection_list.addItem(item)
    
    def on_connection_selected(self, item):
        self.current_connection = item.conn_id
        self.chat_display.clear()
        
        # 加载聊天记录
        messages = self.db.get_messages(self.current_connection)
        for msg in messages:
            sender, message, timestamp, file_path = msg
            self.show_message(sender, message, file_path)
    
    def attach_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "所有文件 (*.*)")
        if file_path:
            self.current_file = file_path
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            self.file_info_label.setText(f"已选择文件: {file_name} ({file_size/1024:.2f} KB)")
            self.file_info_label.setVisible(True)
    
    def send_message(self):
        if not self.current_connection:
            QMessageBox.warning(self, "未选择连接", "请先选择一个连接")
            return
            
        if not self.client_socket:
            QMessageBox.warning(self, "未连接", "没有活动连接，请先连接")
            return
            
        # 处理文件发送
        if self.current_file:
            file_name = os.path.basename(self.current_file)
            file_size = os.path.getsize(self.current_file)
            
            # 发送文件信息
            file_info = {
                'type': 'file',
                'file_name': file_name,
                'file_size': file_size
            }
            try:
                self.client_socket.sendall(json.dumps(file_info).encode('utf-8'))
                self.db.save_message(self.current_connection, "我", f"[文件] {file_name}", self.current_file)
                self.show_message("我", f"[文件] {file_name}")
                
                # 分块发送文件内容
                with open(self.current_file, 'rb') as f:
                    while True:
                        data = f.read(4096)
                        if not data:
                            break
                        self.client_socket.sendall(data)
                
                self.current_file = None
                self.file_info_label.setVisible(False)
                self.show_system_message("文件发送完成")
            except Exception as e:
                self.show_system_message(f"文件发送失败: {str(e)}")
            return
        
        # 处理文本消息
        message = self.message_input.toPlainText().strip()
        if not message:
            return
            
        try:
            # 发送消息
            msg_data = {
                'type': 'text',
                'content': message
            }
            self.client_socket.sendall(json.dumps(msg_data).encode('utf-8'))
            
            # 保存到数据库
            self.db.save_message(self.current_connection, "我", message)
            
            # 显示消息
            self.show_message("我", message)
            
            # 清空输入框
            self.message_input.clear()
        except Exception as e:
            self.show_system_message(f"发送失败: {str(e)}")
    
    def show_message(self, sender, message, file_path=None):
        # 添加时间戳
        timestamp = datetime.datetime.now().strftime("%H:%M")
        
        # 格式化消息
        if sender == "我":
            text = f'<div style="margin: 10px 20px 10px 100px;">'
            text += f'<div style="background-color: #0078D7; color: white; border-radius: 10px; padding: 8px 12px; float: right; max-width: 70%;">'
            if file_path:
                file_name = os.path.basename(file_path)
                text += f'<div style="font-weight: bold;">[文件] {file_name}</div>'
            else:
                text += message
            text += f'<div style="font-size: 10px; text-align: right; opacity: 0.8; margin-top: 5px;">{timestamp}</div>'
            text += '</div>'
            text += '<div style="clear: both;"></div>'
            text += '</div>'
        else:
            text = f'<div style="margin: 10px 100px 10px 20px;">'
            text += f'<div style="background-color: #E0E0E0; color: black; border-radius: 10px; padding: 8px 12px; float: left; max-width: 70%;">'
            if file_path:
                file_name = os.path.basename(file_path)
                text += f'<div style="font-weight: bold;">[文件] {file_name}</div>'
            else:
                text += message
            text += f'<div style="font-size: 10px; text-align: left; opacity: 0.8; margin-top: 5px;">{timestamp}</div>'
            text += '</div>'
            text += '<div style="clear: both;"></div>'
            text += '</div>'
        
        self.chat_display.append(text)
        
        # 滚动到底部
        scroll_bar = self.chat_display.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
    
    def show_system_message(self, message):
        text = f'<div style="text-align: center; color: #606060; margin: 10px;">'
        text += f'<div style="font-size: 12px; font-style: italic;">{message}</div>'
        text += '</div>'
        
        self.chat_display.append(text)
        
        # 滚动到底部
        scroll_bar = self.chat_display.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
    
    def export_chat_history(self):
        if not self.current_connection:
            QMessageBox.warning(self, "未选择连接", "请先选择一个连接")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出聊天记录", "", "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                self.db.export_chat(self.current_connection, file_path)
                QMessageBox.information(self, "导出成功", f"聊天记录已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出失败: {str(e)}")
    
    def closeEvent(self, event):
        # 关闭时清理资源
        self.listening = False
        try:
            if self.server_socket:
                self.server_socket.close()
            if self.client_socket:
                self.client_socket.close()
        except:
            pass
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = ChatWindow()
    window.show()
    sys.exit(app.exec_())