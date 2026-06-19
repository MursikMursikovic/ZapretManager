import os
import sys
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pathlib import Path
import psutil
from datetime import datetime
import ctypes
import requests
import webbrowser

class ZapretManager:
    def __init__(self, root):
        self.root = root
        self.root.title("ZapretManager v1.0.2")
        self.root.geometry("1100x850")
        self.root.minsize(900, 700)
        
        # Классические цвета Windows 95/98
        self.colors = {
            'bg': '#008080',
            'bg2': '#c0c0c0',
            'bg3': '#e0e0e0',
            'fg': '#000000',
            'fg2': '#000000',
            'accent': '#000080',
            'accent2': '#000080',
            'success': '#008000',
            'success2': '#008000',
            'warning': '#808000',
            'error': '#800000',
            'info': '#000080',
            'card_bg': '#c0c0c0',
            'card_header': '#000080',
            'border': '#808080',
            'log_bg': '#ffffff',
            'log_fg': '#000000',
            'btn_bg': '#c0c0c0',
            'btn_fg': '#000000',
            'highlight': '#ffffff',
            'shadow': '#808080'
        }
        
        # Проверка прав администратора
        self.is_admin = self.is_admin_user()
        if not self.is_admin:
            self.request_admin_rights()
            return
            
        # Переменные
        self.zapret_path = tk.StringVar()
        self.selected_strategy = tk.StringVar(value="general (ALT).bat")
        self.is_running = False
        self.process = None
        self.process_pid = None
        self.testing = False
        self.test_results = {}
        self.best_strategy = None
        self.auto_start_after_test = tk.BooleanVar(value=True)
        
        # Статусы
        self.service_status = tk.StringVar(value="Неизвестно")
        self.game_filter_status = tk.StringVar(value="unknown")
        self.ipset_filter_status = tk.StringVar(value="unknown")
        self.test_status = tk.StringVar(value="Готов к работе")
        
        # Список стратегий
        self.strategies = []
        
        # Сайты для проверки
        self.test_sites = [
            "https://youtube.com",
            "https://discord.com",
            "https://google.com"
        ]
        
        # НАСТРОЙКА СТИЛЕЙ (до создания log_text)
        self.setup_styles()
        
        # СОЗДАНИЕ UI (здесь создается log_text)
        self.create_widgets()
        
        # ТЕПЕРЬ можно использовать log()
        self.log("Добро пожаловать в ZapretManager v1.0.2")
        self.log("Права администратора: ДА")
        
        # Автоопределение пути (после создания UI)
        self.auto_detect_path()
        
        # Обновление списка стратегий
        self.refresh_strategies()
        
        # Запуск мониторинга
        self.start_monitoring()
        
    def auto_detect_path(self):
        """Улучшенное автоматическое определение пути"""
        # Получаем пути для поиска
        search_paths = []
        
        # 1. Текущая папка
        current_dir = Path.cwd()
        search_paths.append(current_dir)
        
        # 2. Папка с исполняемым файлом
        if hasattr(sys, '_MEIPASS'):  # Если запущено как .exe
            exe_dir = Path(sys._MEIPASS)
            search_paths.append(exe_dir)
        else:
            script_dir = Path(sys.argv[0]).parent
            search_paths.append(script_dir)
            # Если мы в папке gui, поднимаемся на уровень выше
            if script_dir.name == "gui":
                search_paths.append(script_dir.parent)
        
        # 3. Папка с .exe файлом (если запущено из dist)
        exe_path = Path(sys.argv[0])
        if exe_path.suffix == '.exe':
            exe_dir = exe_path.parent
            search_paths.append(exe_dir)
            # Если мы в папке dist, поднимаемся на уровень выше
            if exe_dir.name == "dist":
                search_paths.append(exe_dir.parent)
        
        # 4. Стандартные пути
        common_paths = [
            "C:\\zapret",
            "C:\\zapret-discord-youtube",
            str(Path.home() / "zapret"),
            str(Path.home() / "Downloads" / "zapret-discord-youtube"),
            str(Path.home() / "Desktop" / "zapret-discord-youtube"),
            "D:\\zapret",
            "D:\\zapret-discord-youtube",
        ]
        search_paths.extend([Path(p) for p in common_paths])
        
        # 5. Поиск по дискам (упрощенный)
        for drive in ['C:', 'D:', 'E:', 'F:']:
            try:
                if os.path.exists(drive):
                    search_paths.append(Path(drive) / "zapret")
                    search_paths.append(Path(drive) / "zapret-discord-youtube")
                    search_paths.append(Path(drive) / "Programs" / "zapret")
            except:
                pass
        
        # Удаляем дубликаты
        search_paths = list(dict.fromkeys(search_paths))
        
        self.log("Поиск папки с zapret...")
        
        # Проверяем каждый путь
        for path in search_paths:
            if not path or not path.exists():
                continue
                
            # Проверяем наличие service.bat или general*.bat
            service_exists = (path / "service.bat").exists()
            general_exists = any(path.glob("general*.bat"))
            
            if service_exists or general_exists:
                self.zapret_path.set(str(path))
                self.log(f"✅ Найдена папка: {path}")
                return
                
            # Проверяем подпапки (на случай если внутри есть папка с программой)
            for subdir in path.iterdir():
                if subdir.is_dir():
                    if (subdir / "service.bat").exists() or any(subdir.glob("general*.bat")):
                        self.zapret_path.set(str(subdir))
                        self.log(f"✅ Найдена папка: {subdir}")
                        return
        
        # Если ничего не найдено - предлагаем выбрать вручную
        self.log("⚠️ Папка не найдена автоматически")
        self.log("Пожалуйста, выберите папку вручную")
        
        # Запрашиваем папку через диалог
        folder = filedialog.askdirectory(
            title="Выберите папку с распакованным архивом zapret-discord-youtube",
            initialdir=str(Path.home())
        )
        if folder:
            self.zapret_path.set(folder)
            self.log(f"✅ Выбрана папка: {folder}")
        else:
            # Если пользователь отменил, используем текущую папку
            self.zapret_path.set(str(Path.cwd()))
            self.log(f"⚠️ Использую текущую папку: {Path.cwd()}")
            
    def setup_styles(self):
        """Настройка классических стилей Windows 95"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('Card.TFrame', background=self.colors['card_bg'], relief='raised', borderwidth=2)
        
        style.configure('TLabel', 
                       background=self.colors['bg'], 
                       foreground=self.colors['fg'], 
                       font=('MS Sans Serif', 8))
        style.configure('Card.TLabel',
                       background=self.colors['card_bg'],
                       foreground=self.colors['fg'],
                       font=('MS Sans Serif', 8))
        style.configure('Header.TLabel',
                       background=self.colors['card_header'],
                       foreground='#ffffff',
                       font=('MS Sans Serif', 8, 'bold'))
        
        style.configure('TButton',
                       background=self.colors['btn_bg'],
                       foreground=self.colors['btn_fg'],
                       borderwidth=2,
                       relief='raised',
                       padding=(10, 4),
                       font=('MS Sans Serif', 8))
        style.map('TButton',
                 background=[('active', self.colors['highlight'])],
                 relief=[('pressed', 'sunken')])
        
        style.configure('Accent.TButton',
                       background=self.colors['btn_bg'],
                       foreground=self.colors['btn_fg'],
                       borderwidth=2,
                       relief='raised',
                       padding=(10, 4),
                       font=('MS Sans Serif', 8, 'bold'))
        style.map('Accent.TButton',
                 background=[('active', self.colors['highlight'])],
                 relief=[('pressed', 'sunken')])
        
        style.configure('Success.TButton',
                       background=self.colors['btn_bg'],
                       foreground='#008000',
                       borderwidth=2,
                       relief='raised',
                       padding=(10, 4),
                       font=('MS Sans Serif', 8, 'bold'))
        style.map('Success.TButton',
                 background=[('active', self.colors['highlight'])],
                 relief=[('pressed', 'sunken')])
        
        style.configure('Danger.TButton',
                       background=self.colors['btn_bg'],
                       foreground='#800000',
                       borderwidth=2,
                       relief='raised',
                       padding=(10, 4),
                       font=('MS Sans Serif', 8, 'bold'))
        style.map('Danger.TButton',
                 background=[('active', self.colors['highlight'])],
                 relief=[('pressed', 'sunken')])
        
        style.configure('Info.TButton',
                       background=self.colors['btn_bg'],
                       foreground=self.colors['fg'],
                       borderwidth=2,
                       relief='raised',
                       padding=(10, 4),
                       font=('MS Sans Serif', 8))
        style.map('Info.TButton',
                 background=[('active', self.colors['highlight'])],
                 relief=[('pressed', 'sunken')])
        
        style.configure('Warning.TButton',
                       background=self.colors['btn_bg'],
                       foreground='#808000',
                       borderwidth=2,
                       relief='raised',
                       padding=(10, 4),
                       font=('MS Sans Serif', 8, 'bold'))
        style.map('Warning.TButton',
                 background=[('active', self.colors['highlight'])],
                 relief=[('pressed', 'sunken')])
        
        style.configure('Modern.TEntry',
                       fieldbackground='#ffffff',
                       foreground='#000000',
                       borderwidth=2,
                       relief='sunken',
                       padding=3,
                       font=('MS Sans Serif', 8))
        
        style.configure('Modern.TCombobox',
                       fieldbackground='#ffffff',
                       foreground='#000000',
                       borderwidth=2,
                       relief='sunken',
                       padding=3,
                       font=('MS Sans Serif', 8))
        
        style.configure('Modern.Horizontal.TProgressbar',
                       background='#000080',
                       troughcolor='#c0c0c0',
                       borderwidth=2,
                       relief='sunken')
        
        style.configure('Modern.Vertical.TScrollbar',
                       background='#c0c0c0',
                       troughcolor='#c0c0c0',
                       borderwidth=2,
                       relief='raised',
                       arrowsize=12)
        
        style.configure('Modern.Treeview',
                       background='#ffffff',
                       foreground='#000000',
                       fieldbackground='#ffffff',
                       borderwidth=2,
                       relief='sunken')
        
    def create_widgets(self):
        """Создание виджетов"""
        # Главный контейнер
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === ХЕДЕР ===
        header_frame = tk.Frame(main_container, bg=self.colors['card_header'], height=55)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        logo_frame = tk.Frame(header_frame, bg=self.colors['card_header'])
        logo_frame.pack(side=tk.LEFT, padx=15)
        
        win_icon = tk.Label(logo_frame,
                           text="🪟",
                           font=('Segoe UI', 20),
                           bg=self.colors['card_header'],
                           fg='#ffffff')
        win_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        title_label = tk.Label(logo_frame, 
                              text="ZapretManager",
                              font=('MS Sans Serif', 18, 'bold'),
                              bg=self.colors['card_header'],
                              fg='#ffffff')
        title_label.pack(side=tk.LEFT)
        
        version_label = tk.Label(logo_frame,
                                text="v1.0.2",
                                font=('MS Sans Serif', 10),
                                bg=self.colors['card_header'],
                                fg='#ffff00')
        version_label.pack(side=tk.LEFT, padx=10)
        
        subtitle = tk.Label(header_frame,
                           text="Управление обходом блокировок Discord & YouTube",
                           font=('MS Sans Serif', 8),
                           bg=self.colors['card_header'],
                           fg='#ffffff')
        subtitle.pack(side=tk.LEFT, padx=20)
        
        admin_frame = tk.Frame(header_frame, bg=self.colors['card_header'])
        admin_frame.pack(side=tk.RIGHT, padx=15)
        
        admin_indicator = tk.Label(admin_frame,
                                  text="[АДМИНИСТРАТОР]",
                                  font=('MS Sans Serif', 8, 'bold'),
                                  bg=self.colors['card_header'],
                                  fg='#00ff00')
        admin_indicator.pack()
        
        # === ОСНОВНАЯ СЕТКА ===
        content_frame = tk.Frame(main_container, bg=self.colors['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        left_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.create_path_section(left_frame)
        self.create_strategy_section(left_frame)
        self.create_control_section(left_frame)
        self.create_extra_section(left_frame)
        
        right_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self.create_status_section(right_frame)
        self.create_results_section(right_frame)
        
        # === ЛОГ === (создается здесь)
        self.create_log_section(main_container)
        
        # === ПРОГРЕСС-БАР ===
        self.progress = ttk.Progressbar(main_container,
                                       style='Modern.Horizontal.TProgressbar',
                                       mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(10, 0))
        
        # === ФУТЕР ===
        self.create_footer(main_container)
        
    def create_path_section(self, parent):
        """Секция пути"""
        card = tk.Frame(parent, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.pack(fill=tk.X, pady=(0, 10))
        
        header = tk.Frame(card, bg=self.colors['card_header'], height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header,
                text=" Путь к программе",
                font=('MS Sans Serif', 8, 'bold'),
                bg=self.colors['card_header'],
                fg='#ffffff').pack(side=tk.LEFT)
        
        btn_find = tk.Button(header,
                            text="Найти",
                            command=self.auto_detect_path,
                            bg=self.colors['btn_bg'],
                            fg=self.colors['btn_fg'],
                            relief='raised',
                            borderwidth=2,
                            padx=10,
                            font=('MS Sans Serif', 8))
        btn_find.pack(side=tk.RIGHT, padx=10)
        
        content = tk.Frame(card, bg=self.colors['card_bg'])
        content.pack(fill=tk.X, padx=10, pady=8)
        
        self.path_entry = ttk.Entry(content,
                                   textvariable=self.zapret_path,
                                   style='Modern.TEntry')
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        btn_browse = tk.Button(content,
                              text="Обзор...",
                              command=self.browse_folder,
                              bg=self.colors['btn_bg'],
                              fg=self.colors['btn_fg'],
                              relief='raised',
                              borderwidth=2,
                              padx=10,
                              font=('MS Sans Serif', 8))
        btn_browse.pack(side=tk.LEFT, padx=2)
        
        btn_refresh = tk.Button(content,
                               text="Обновить",
                               command=self.refresh_strategies,
                               bg=self.colors['btn_bg'],
                               fg=self.colors['btn_fg'],
                               relief='raised',
                               borderwidth=2,
                               padx=10,
                               font=('MS Sans Serif', 8))
        btn_refresh.pack(side=tk.LEFT, padx=2)
        
    def create_strategy_section(self, parent):
        """Секция стратегии"""
        card = tk.Frame(parent, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.pack(fill=tk.X, pady=(0, 10))
        
        header = tk.Frame(card, bg=self.colors['card_header'], height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header,
                text=" Выбор стратегии",
                font=('MS Sans Serif', 8, 'bold'),
                bg=self.colors['card_header'],
                fg='#ffffff').pack(side=tk.LEFT)
        
        content = tk.Frame(card, bg=self.colors['card_bg'])
        content.pack(fill=tk.X, padx=10, pady=8)
        
        strategy_row = tk.Frame(content, bg=self.colors['card_bg'])
        strategy_row.pack(fill=tk.X)
        
        self.strategy_combo = ttk.Combobox(strategy_row,
                                          textvariable=self.selected_strategy,
                                          style='Modern.TCombobox',
                                          width=35)
        self.strategy_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        btn_auto = tk.Button(strategy_row,
                            text="Автоподбор",
                            command=self.auto_test_strategies,
                            bg=self.colors['btn_bg'],
                            fg='#008000',
                            relief='raised',
                            borderwidth=2,
                            padx=15,
                            font=('MS Sans Serif', 8, 'bold'))
        btn_auto.pack(side=tk.LEFT)
        
        auto_frame = tk.Frame(content, bg=self.colors['card_bg'])
        auto_frame.pack(fill=tk.X, pady=(8, 0))
        
        self.auto_check = tk.Checkbutton(auto_frame,
                                        text="Автоматический запуск после подбора",
                                        variable=self.auto_start_after_test,
                                        bg=self.colors['card_bg'],
                                        fg=self.colors['fg'],
                                        font=('MS Sans Serif', 8))
        self.auto_check.pack(side=tk.LEFT)
        
    def create_control_section(self, parent):
        """Секция управления"""
        card = tk.Frame(parent, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.pack(fill=tk.X, pady=(0, 10))
        
        header = tk.Frame(card, bg=self.colors['card_header'], height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header,
                text=" Управление",
                font=('MS Sans Serif', 8, 'bold'),
                bg=self.colors['card_header'],
                fg='#ffffff').pack(side=tk.LEFT)
        
        content = tk.Frame(card, bg=self.colors['card_bg'])
        content.pack(fill=tk.X, padx=10, pady=8)
        
        self.start_btn = tk.Button(content,
                                  text="▶ Запустить",
                                  command=self.start_zapret,
                                  bg=self.colors['btn_bg'],
                                  fg='#008000',
                                  relief='raised',
                                  borderwidth=2,
                                  padx=15,
                                  font=('MS Sans Serif', 8, 'bold'))
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.btn_stop = tk.Button(content,
                                 text="⏹ Остановить",
                                 command=self.stop_zapret,
                                 bg=self.colors['btn_bg'],
                                 fg='#800000',
                                 relief='raised',
                                 borderwidth=2,
                                 padx=15,
                                 font=('MS Sans Serif', 8, 'bold'),
                                 state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=2)
        
        btn_restart = tk.Button(content,
                               text="🔄 Перезапустить",
                               command=self.restart_zapret,
                               bg=self.colors['btn_bg'],
                               fg=self.colors['fg'],
                               relief='raised',
                               borderwidth=2,
                               padx=15,
                               font=('MS Sans Serif', 8))
        btn_restart.pack(side=tk.LEFT, padx=2)
        
        btn_force = tk.Button(content,
                             text="💀 Убить все",
                             command=self.force_kill_all,
                             bg=self.colors['btn_bg'],
                             fg='#800000',
                             relief='raised',
                             borderwidth=2,
                             padx=15,
                             font=('MS Sans Serif', 8, 'bold'))
        btn_force.pack(side=tk.LEFT, padx=2)
        
    def create_extra_section(self, parent):
        """Секция дополнительных функций"""
        card = tk.Frame(parent, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.pack(fill=tk.X)
        
        header = tk.Frame(card, bg=self.colors['card_header'], height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header,
                text=" Дополнительно",
                font=('MS Sans Serif', 8, 'bold'),
                bg=self.colors['card_header'],
                fg='#ffffff').pack(side=tk.LEFT)
        
        content = tk.Frame(card, bg=self.colors['card_bg'])
        content.pack(fill=tk.X, padx=10, pady=8)
        
        row1 = tk.Frame(content, bg=self.colors['card_bg'])
        row1.pack(fill=tk.X, pady=(0, 4))
        
        btn_install = tk.Button(row1,
                               text="Установить службу",
                               command=self.install_service,
                               bg=self.colors['btn_bg'],
                               fg=self.colors['fg'],
                               relief='raised',
                               borderwidth=2,
                               padx=12,
                               font=('MS Sans Serif', 8))
        btn_install.pack(side=tk.LEFT, padx=2)
        
        btn_remove = tk.Button(row1,
                              text="Удалить службу",
                              command=self.remove_service,
                              bg=self.colors['btn_bg'],
                              fg=self.colors['fg'],
                              relief='raised',
                              borderwidth=2,
                              padx=12,
                              font=('MS Sans Serif', 8))
        btn_remove.pack(side=tk.LEFT, padx=2)
        
        btn_check = tk.Button(row1,
                             text="Проверить статус",
                             command=self.check_status,
                             bg=self.colors['btn_bg'],
                             fg=self.colors['fg'],
                             relief='raised',
                             borderwidth=2,
                             padx=12,
                             font=('MS Sans Serif', 8))
        btn_check.pack(side=tk.LEFT, padx=2)
        
        row2 = tk.Frame(content, bg=self.colors['card_bg'])
        row2.pack(fill=tk.X)
        
        btn_update = tk.Button(row2,
                              text="Обновить списки",
                              command=self.update_lists,
                              bg=self.colors['btn_bg'],
                              fg=self.colors['fg'],
                              relief='raised',
                              borderwidth=2,
                              padx=12,
                              font=('MS Sans Serif', 8))
        btn_update.pack(side=tk.LEFT, padx=2)
        
        btn_hosts = tk.Button(row2,
                             text="Обновить hosts",
                             command=self.update_hosts,
                             bg=self.colors['btn_bg'],
                             fg=self.colors['fg'],
                             relief='raised',
                             borderwidth=2,
                             padx=12,
                             font=('MS Sans Serif', 8))
        btn_hosts.pack(side=tk.LEFT, padx=2)
        
        btn_diagnostic = tk.Button(row2,
                                  text="Диагностика",
                                  command=self.run_diagnostics,
                                  bg=self.colors['btn_bg'],
                                  fg=self.colors['fg'],
                                  relief='raised',
                                  borderwidth=2,
                                  padx=12,
                                  font=('MS Sans Serif', 8))
        btn_diagnostic.pack(side=tk.LEFT, padx=2)
        
    def create_status_section(self, parent):
        """Секция статуса"""
        card = tk.Frame(parent, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.pack(fill=tk.X, pady=(0, 10))
        
        header = tk.Frame(card, bg=self.colors['card_header'], height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header,
                text=" Системный статус",
                font=('MS Sans Serif', 8, 'bold'),
                bg=self.colors['card_header'],
                fg='#ffffff').pack(side=tk.LEFT)
        
        content = tk.Frame(card, bg=self.colors['card_bg'])
        content.pack(fill=tk.X, padx=10, pady=8)
        
        status_items = [
            ("Состояние:", "status_label", "Не запущен", "red"),
            ("PID:", "pid_label", "-", "black"),
            ("Лучшая стратегия:", "best_label", "Не найдена", "black"),
            ("Служба:", "service_status", "Неизвестно", "black"),
            ("Game Filter:", "game_filter_status", "unknown", "black"),
            ("IPSet Filter:", "ipset_filter_status", "unknown", "black"),
            ("Тестирование:", "test_status", "Готов к работе", "green"),
        ]
        
        for i, (label_text, attr_name, default, color) in enumerate(status_items):
            row = i // 2
            col = i % 2
            frame = tk.Frame(content, bg=self.colors['card_bg'])
            frame.grid(row=row, column=col, sticky='w', padx=(0, 20), pady=1)
            
            tk.Label(frame,
                    text=label_text,
                    font=('MS Sans Serif', 8),
                    bg=self.colors['card_bg'],
                    fg='#000000',
                    width=16,
                    anchor='w').pack(side=tk.LEFT)
            
            label = tk.Label(frame,
                            text=default,
                            font=('MS Sans Serif', 8, 'bold'),
                            bg=self.colors['card_bg'],
                            fg=color,
                            anchor='w')
            label.pack(side=tk.LEFT)
            setattr(self, attr_name, label)
        
    def create_results_section(self, parent):
        """Секция результатов"""
        card = tk.Frame(parent, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.pack(fill=tk.X, pady=(0, 10))
        
        header = tk.Frame(card, bg=self.colors['card_header'], height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header,
                text=" Результаты тестирования",
                font=('MS Sans Serif', 8, 'bold'),
                bg=self.colors['card_header'],
                fg='#ffffff').pack(side=tk.LEFT)
        
        content = tk.Frame(card, bg=self.colors['card_bg'])
        content.pack(fill=tk.X, padx=10, pady=8)
        
        tree_frame = tk.Frame(content, bg=self.colors['card_bg'])
        tree_frame.pack(fill=tk.X)
        
        columns = ("strategy", "status", "sites", "time")
        self.results_tree = ttk.Treeview(tree_frame,
                                        columns=columns,
                                        height=3,
                                        show="headings",
                                        style='Modern.Treeview')
        
        self.results_tree.heading("strategy", text="Стратегия")
        self.results_tree.heading("status", text="Статус")
        self.results_tree.heading("sites", text="Сайты")
        self.results_tree.heading("time", text="Время")
        
        self.results_tree.column("strategy", width=200)
        self.results_tree.column("status", width=150)
        self.results_tree.column("sites", width=120)
        self.results_tree.column("time", width=70)
        
        self.results_tree.pack(fill=tk.X)
        
        btn_clear = tk.Button(content,
                             text="Очистить результаты",
                             command=self.clear_results,
                             bg=self.colors['btn_bg'],
                             fg=self.colors['fg'],
                             relief='raised',
                             borderwidth=2,
                             padx=10,
                             font=('MS Sans Serif', 8))
        btn_clear.pack(pady=(8, 0))
        
    def create_log_section(self, parent):
        """Секция лога"""
        card = tk.Frame(parent, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        header = tk.Frame(card, bg=self.colors['card_header'], height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header,
                text=" Лог операций",
                font=('MS Sans Serif', 8, 'bold'),
                bg=self.colors['card_header'],
                fg='#ffffff').pack(side=tk.LEFT)
        
        log_btn_frame = tk.Frame(header, bg=self.colors['card_header'])
        log_btn_frame.pack(side=tk.RIGHT, padx=10)
        
        btn_clear = tk.Button(log_btn_frame,
                             text="Очистить",
                             command=self.clear_log,
                             bg=self.colors['btn_bg'],
                             fg=self.colors['fg'],
                             relief='raised',
                             borderwidth=2,
                             padx=10,
                             font=('MS Sans Serif', 8))
        btn_clear.pack(side=tk.LEFT, padx=2)
        
        btn_save = tk.Button(log_btn_frame,
                            text="Сохранить",
                            command=self.save_log,
                            bg=self.colors['btn_bg'],
                            fg=self.colors['fg'],
                            relief='raised',
                            borderwidth=2,
                            padx=10,
                            font=('MS Sans Serif', 8))
        btn_save.pack(side=tk.LEFT, padx=2)
        
        content = tk.Frame(card, bg=self.colors['card_bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        log_container = tk.Frame(content, bg='#ffffff', relief='sunken', borderwidth=2)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_container,
                                                 height=6,
                                                 bg='#ffffff',
                                                 fg='#000000',
                                                 insertbackground='#000000',
                                                 font=('Courier New', 9),
                                                 borderwidth=0,
                                                 relief='flat',
                                                 wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Настройка тегов для цветного лога
        self.log_text.tag_config('timestamp', foreground='#808080')
        self.log_text.tag_config('success', foreground='#008000')
        self.log_text.tag_config('error', foreground='#800000')
        self.log_text.tag_config('warning', foreground='#808000')
        self.log_text.tag_config('info', foreground='#000080')
        self.log_text.tag_config('accent', foreground='#000080')
        
    def create_footer(self, parent):
        """Футер"""
        footer = tk.Frame(parent, bg=self.colors['bg'], height=25)
        footer.pack(fill=tk.X, pady=(10, 0))
        footer.pack_propagate(False)
        
        tk.Label(footer,
                text="Автоподбор тестирует все стратегии и выбирает лучшую",
                font=('MS Sans Serif', 8),
                bg=self.colors['bg'],
                fg='#ffffff').pack(side=tk.LEFT)
        
        tk.Label(footer,
                text="Работает с правами администратора",
                font=('MS Sans Serif', 8),
                bg=self.colors['bg'],
                fg='#ffffff').pack(side=tk.RIGHT)
        
        github_link = tk.Label(footer,
                              text="GitHub",
                              font=('MS Sans Serif', 8, 'underline'),
                              bg=self.colors['bg'],
                              fg='#ffffff',
                              cursor='hand2')
        github_link.pack(side=tk.RIGHT, padx=10)
        github_link.bind('<Button-1>', lambda e: webbrowser.open('https://github.com/Flowseal/zapret-discord-youtube'))
        
    def log(self, message):
        """Добавление сообщения в лог"""
        # Проверяем, существует ли log_text
        if not hasattr(self, 'log_text'):
            # Если log_text еще не создан, просто выводим в консоль
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
            return
            
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if '✅' in message or '✔' in message or 'успешно' in message:
            tag = 'success'
        elif '❌' in message or '⚠️' in message or 'ошибк' in message.lower():
            tag = 'error'
        elif '🚀' in message or '▶' in message:
            tag = 'accent'
        elif '🔍' in message or '📋' in message or '🔄' in message:
            tag = 'info'
        elif '⚠️' in message:
            tag = 'warning'
        else:
            tag = 'info'
            
        self.log_text.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        self.log_text.insert(tk.END, f"{message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    # ===== ОСТАЛЬНЫЕ МЕТОДЫ =====
    
    def force_kill_all(self):
        if not messagebox.askyesno("Подтверждение", 
                                  "Это завершит ВСЕ процессы winws.exe и cmd.exe связанные с zapret.\n\n"
                                  "Продолжить?"):
            return
            
        self.log("Принудительное завершение всех процессов...")
        self.progress.start()
        
        try:
            killed = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    if proc_info['name'] and 'winws.exe' in proc_info['name'].lower():
                        proc.kill()
                        killed += 1
                        self.log(f"Убит winws.exe (PID: {proc_info['pid']})")
                except:
                    pass
                    
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    if proc_info['name'] and 'cmd.exe' in proc_info['name'].lower():
                        if proc_info['cmdline']:
                            cmdline = ' '.join(proc_info['cmdline']).lower()
                            if 'general' in cmdline or 'zapret' in cmdline or 'winws' in cmdline:
                                proc.kill()
                                killed += 1
                                self.log(f"Убита cmd.exe (PID: {proc_info['pid']})")
                except:
                    pass
                    
            self.is_running = False
            self.process = None
            self.process_pid = None
            
            self.status_label.config(text="Остановлен", fg="#800000")
            self.pid_label.config(text="-", fg="black")
            self.start_btn.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            
            self.log(f"Принудительно завершено процессов: {killed}")
            
        except Exception as e:
            self.log(f"Ошибка: {e}")
        finally:
            self.progress.stop()
            
    def start_zapret(self):
        if self.is_running:
            self.log("Уже запущено")
            return
            
        if self.best_strategy:
            strategy = self.best_strategy["name"]
            self.selected_strategy.set(strategy)
            self.log(f"Использую лучшую стратегию: {strategy}")
        else:
            strategy = self.selected_strategy.get()
            
        strategy_path = Path(self.zapret_path.get()) / strategy
        
        if not strategy_path.exists():
            messagebox.showerror("Ошибка", f"Файл не найден:\n{strategy_path}\n\n"
                               f"Проверьте путь: {self.zapret_path.get()}")
            return
            
        try:
            self.log(f"Запуск: {strategy}")
            self.progress.start()
            
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "open",
                str(strategy_path),
                None,
                str(strategy_path.parent),
                1
            )
            
            if result <= 32:
                raise Exception(f"Ошибка запуска (код: {result})")
                
            self.is_running = True
            
            self.status_label.config(text="Запущен", fg="#008000")
            self.pid_label.config(text="см. консоль", fg="black")
            self.start_btn.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            
            self.log("Запущен успешно")
            self.root.after(3000, self.check_winws)
            
        except Exception as e:
            self.log(f"Ошибка: {e}")
            messagebox.showerror("Ошибка", str(e))
        finally:
            self.progress.stop()
            
    def check_winws(self):
        found_pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'winws.exe' in proc.info['name'].lower():
                    found_pids.append(str(proc.info['pid']))
            except:
                pass
                
        if found_pids:
            self.log(f"Найден winws.exe (PID: {', '.join(found_pids)})")
            self.pid_label.config(text=', '.join(found_pids), fg="#008000")
        else:
            self.log("winws.exe не найден")
            self.pid_label.config(text="Не найден", fg="#800000")
            
    def stop_zapret(self):
        if not self.is_running:
            self.log("Не запущено")
            return
            
        self.log("Остановка...")
        self.progress.start()
        
        try:
            killed = 0
            
            if self.process:
                try:
                    self.process.terminate()
                    time.sleep(1)
                    if self.process.poll() is None:
                        self.process.kill()
                    killed += 1
                    self.log("Завершен основной процесс")
                except:
                    pass
                    
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'winws.exe' in proc.info['name'].lower():
                        proc.terminate()
                        time.sleep(0.5)
                        if proc.is_running():
                            proc.kill()
                        killed += 1
                        self.log(f"Завершен winws.exe (PID: {proc.info['pid']})")
                except:
                    pass
                    
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'cmd.exe' in proc.info['name'].lower():
                        if proc.info['cmdline']:
                            cmdline = ' '.join(proc.info['cmdline']).lower()
                            if 'general' in cmdline or 'zapret' in cmdline:
                                proc.terminate()
                                time.sleep(0.5)
                                if proc.is_running():
                                    proc.kill()
                                killed += 1
                                self.log(f"Завершена cmd (PID: {proc.info['pid']})")
                except:
                    pass
                    
            self.is_running = False
            self.process = None
            self.process_pid = None
            
            self.status_label.config(text="Остановлен", fg="#800000")
            self.pid_label.config(text="-", fg="black")
            self.start_btn.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            
            self.log(f"Остановлен. Завершено процессов: {killed}")
            
        except Exception as e:
            self.log(f"Ошибка: {e}")
        finally:
            self.progress.stop()
            
    def restart_zapret(self):
        self.log("Перезапуск...")
        if self.is_running:
            self.stop_zapret()
            time.sleep(2)
        self.start_zapret()
        
    def start_monitoring(self):
        def monitor():
            while True:
                try:
                    if self.is_running:
                        found = False
                        for proc in psutil.process_iter(['name']):
                            try:
                                if proc.info['name'] and 'winws.exe' in proc.info['name'].lower():
                                    found = True
                                    break
                            except:
                                pass
                                
                        if not found:
                            found_cmd = False
                            for proc in psutil.process_iter(['name', 'cmdline']):
                                try:
                                    if proc.info['name'] and 'cmd.exe' in proc.info['name'].lower():
                                        if proc.info['cmdline']:
                                            cmdline = ' '.join(proc.info['cmdline']).lower()
                                            if 'general' in cmdline or 'zapret' in cmdline:
                                                found_cmd = True
                                                break
                                except:
                                    pass
                                    
                            if not found_cmd and not found:
                                self.root.after(0, self._process_died)
                                
                    time.sleep(5)
                except:
                    time.sleep(5)
                    
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        
    def _process_died(self):
        if not self.is_running:
            return
            
        self.is_running = False
        self.process = None
        
        self.status_label.config(text="Процесс завершен", fg="orange")
        self.pid_label.config(text="-", fg="black")
        self.start_btn.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        
        self.log("Процесс завершен (возможно, вручную)")
        
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с распакованным архивом zapret-discord-youtube")
        if folder:
            self.zapret_path.set(folder)
            self.refresh_strategies()
            self.log(f"Путь изменен: {folder}")
            
    def refresh_strategies(self):
        path = Path(self.zapret_path.get())
        if not path.exists():
            self.log(f"⚠️ Папка не существует: {path}")
            self.log("Пожалуйста, выберите правильную папку через 'Обзор'")
            self.strategy_combo['values'] = []
            return
            
        strategies = []
        for file in sorted(path.glob("general*.bat")):
            if file.name != "service.bat":
                strategies.append(file.name)
                
        if strategies:
            self.strategies = strategies
            self.strategy_combo['values'] = strategies
            if self.selected_strategy.get() not in strategies:
                self.selected_strategy.set(strategies[0])
            self.log(f"✅ Найдено стратегий: {len(strategies)}")
        else:
            self.log("⚠️ Стратегии не найдены!")
            self.log(f"Проверьте папку: {path}")
            self.log("В папке должны быть файлы general*.bat")
            self.strategy_combo['values'] = []
            
    def clear_log(self):
        if not hasattr(self, 'log_text'):
            return
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log("Лог очищен")
        
    def save_log(self):
        if not hasattr(self, 'log_text'):
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt")]
        )
        if file_path:
            try:
                content = self.log_text.get(1.0, tk.END)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log(f"Лог сохранен: {file_path}")
            except Exception as e:
                self.log(f"Ошибка сохранения: {e}")
                
    def clear_results(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.test_results.clear()
        self.best_strategy = None
        self.best_label.config(text="Не найдена", fg="black")
        self.log("Результаты очищены")
        
    def check_site_available(self, url, timeout=5):
        try:
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            return response.status_code == 200
        except:
            return False
            
    def test_strategy(self, strategy_name):
        self.log(f"Тестирование: {strategy_name}")
        
        strategy_path = Path(self.zapret_path.get()) / strategy_name
        if not strategy_path.exists():
            return {"name": strategy_name, "working": False, "reason": "Файл не найден"}
            
        try:
            process = subprocess.Popen(
                f'"{strategy_path}"',
                shell=True,
                cwd=str(strategy_path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            time.sleep(3)
            
            winws_found = False
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and 'winws.exe' in proc.info['name'].lower():
                        winws_found = True
                        break
                except:
                    pass
                    
            if not winws_found:
                process.terminate()
                time.sleep(1)
                if process.poll() is None:
                    process.kill()
                return {"name": strategy_name, "working": False, "reason": "winws.exe не запустился"}
                
            working_sites = []
            for site in self.test_sites:
                if self.check_site_available(site):
                    working_sites.append(site)
                    
            process.terminate()
            time.sleep(1)
            if process.poll() is None:
                process.kill()
                
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'winws.exe' in proc.info['name'].lower():
                        proc.kill()
                except:
                    pass
                    
            working = len(working_sites) >= 1
            return {
                "name": strategy_name,
                "working": working,
                "sites": working_sites,
                "count": len(working_sites),
                "all_sites": self.test_sites.copy()
            }
            
        except Exception as e:
            return {"name": strategy_name, "working": False, "reason": str(e)}
            
    def auto_test_strategies(self):
        if self.testing:
            self.log("Тестирование уже выполняется")
            return
            
        if not self.strategies:
            messagebox.showerror("Ошибка", 
                "Нет стратегий для тестирования!\n\n"
                f"Проверьте путь: {self.zapret_path.get()}\n"
                "В папке должны быть файлы general*.bat")
            return
            
        self.log("Проверка интернет-соединения...")
        if not self.check_site_available("https://google.com", timeout=3):
            messagebox.showerror("Ошибка", "Нет интернет-соединения!")
            return
            
        self.testing = True
        self.test_status.config(text="Тестирование...", fg="#808000")
        self.progress.start()
        self.clear_results()
        
        def run_tests():
            self.log("Начинаю автоподбор стратегий...")
            self.log(f"Всего стратегий: {len(self.strategies)}")
            
            results = []
            working_strategies = []
            start_time = time.time()
            
            for i, strategy in enumerate(self.strategies, 1):
                self.log(f"Тест {i}/{len(self.strategies)}: {strategy}")
                self.root.after(0, lambda s=strategy: self.test_status.config(text=f"Тестирование: {s}", fg="#808000"))
                
                test_start = time.time()
                result = self.test_strategy(strategy)
                test_time = round(time.time() - test_start, 1)
                
                result["time"] = test_time
                results.append(result)
                
                if result["working"]:
                    working_strategies.append(result)
                    status = f"РАБОТАЕТ ({result['count']} сайтов)"
                    sites_info = ', '.join(result['sites'])
                    self.log(f"{strategy} - РАБОТАЕТ: {sites_info}")
                else:
                    reason = result.get("reason", "Неизвестная ошибка")
                    status = f"НЕ РАБОТАЕТ ({reason})"
                    self.log(f"{strategy} - НЕ РАБОТАЕТ ({reason})")
                    sites_info = "-"
                    
                self.root.after(0, lambda s=strategy, st=status, si=sites_info, t=test_time: 
                    self.results_tree.insert("", "end", values=(s, st, si, f"{t}с")))
                    
            total_time = round(time.time() - start_time, 1)
            self.root.after(0, self._finish_testing, working_strategies, total_time)
            
        thread = threading.Thread(target=run_tests, daemon=True)
        thread.start()
        
    def _finish_testing(self, working_strategies, total_time):
        self.testing = False
        self.progress.stop()
        
        if working_strategies:
            best = max(working_strategies, key=lambda x: x["count"])
            self.best_strategy = best
            self.selected_strategy.set(best["name"])
            self.best_label.config(text=best["name"], fg="#008000")
            self.test_status.config(text="Готов к работе", fg="#008000")
            
            self.log(f"Лучшая стратегия: {best['name']} ({best['count']} сайтов)")
            self.log(f"Работающие сайты: {', '.join(best['sites'])}")
            self.log(f"Время тестирования: {total_time}с")
            
            messagebox.showinfo(
                "Автоподбор завершен",
                f"Найдена рабочая стратегия:\n\n"
                f" {best['name']}\n"
                f"Работает: {best['count']} сайтов\n"
                f"{', '.join(best['sites'])}\n"
                f"Время: {total_time}с"
            )
            
            if self.auto_start_after_test.get():
                self.log("Автоматический запуск лучшей стратегии...")
                self.root.after(1000, self.start_zapret)
            else:
                self.log("Автозапуск отключен. Нажмите 'Запустить' вручную.")
        else:
            self.best_strategy = None
            self.best_label.config(text="Не найдена", fg="#800000")
            self.test_status.config(text="Стратегии не найдены", fg="#800000")
            self.log("Рабочих стратегий не найдено!")
            
            messagebox.showwarning(
                "Автоподбор завершен",
                "Рабочих стратегий не найдено!\n\n"
                "Возможные причины:\n"
                "• Стратегии устарели\n"
                "• Провайдер блокирует DPI-обход\n"
                "• Нет интернет-соединения\n\n"
                "Попробуйте обновить списки вручную."
            )
            
    def run_service_command(self, command):
        service_path = Path(self.zapret_path.get()) / "service.bat"
        if not service_path.exists():
            self.log(f"service.bat не найден в {self.zapret_path.get()}")
            return None
            
        try:
            process = subprocess.Popen(
                f'"{service_path}" {command}',
                shell=True,
                cwd=str(self.zapret_path.get()),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='cp866'
            )
            stdout, stderr = process.communicate(timeout=30)
            return stdout
        except Exception as e:
            self.log(f"Ошибка: {e}")
            return None
            
    def install_service(self):
        strategy = self.selected_strategy.get()
        if not messagebox.askyesno("Подтверждение", f"Установить службу с '{strategy}'?"):
            return
            
        self.log(f"Установка службы: {strategy}")
        self.run_service_command("1")
        time.sleep(2)
        self.check_status()
        
    def remove_service(self):
        if not messagebox.askyesno("Подтверждение", "Удалить все службы?"):
            return
            
        self.log("Удаление служб...")
        self.run_service_command("2")
        self.service_status.config(text="Не установлена", fg="black")
        self.log("Службы удалены")
        
    def check_status(self):
        self.log("Проверка статуса...")
        result = self.run_service_command("3")
        
        if result:
            if "Game Filter" in result:
                if "enabled" in result.lower():
                    self.game_filter_status.config(text="ENABLED", fg="#008000")
                else:
                    self.game_filter_status.config(text="DISABLED", fg="#800000")
                    
            if "IPSet Filter" in result:
                if "loaded" in result.lower():
                    self.ipset_filter_status.config(text="loaded", fg="#008000")
                elif "any" in result.lower():
                    self.ipset_filter_status.config(text="any", fg="#808000")
                else:
                    self.ipset_filter_status.config(text="none", fg="black")
                    
            if "Service" in result:
                if "not" in result.lower():
                    self.service_status.config(text="Не установлена", fg="black")
                else:
                    self.service_status.config(text="Установлена", fg="#008000")
                    
    def update_lists(self):
        self.log("Обновление списков...")
        self.run_service_command("8")
        self.log("Команда отправлена")
        
    def update_hosts(self):
        self.log("Обновление hosts...")
        self.run_service_command("9")
        self.log("Команда отправлена")
        
    def run_diagnostics(self):
        self.log("Диагностика...")
        self.run_service_command("11")
        self.log("Команда отправлена")
        
    def is_admin_user(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
            
    def request_admin_rights(self):
        try:
            script = os.path.abspath(sys.argv[0])
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                f'"{script}"',
                None,
                1
            )
            self.root.quit()
            sys.exit()
        except Exception as e:
            messagebox.showerror(
                "Ошибка", 
                f"Не удалось получить права администратора!\n\n"
                f"Запустите программу от имени администратора.\n\n"
                f"Ошибка: {e}"
            )
            sys.exit()
            
    def on_closing(self):
        if self.is_running:
            if messagebox.askyesno("Подтверждение", "Остановить перед закрытием?"):
                self.stop_zapret()
        self.root.destroy()

def main():
    root = tk.Tk()
    
    try:
        root.iconbitmap(default='icon.ico')
    except:
        pass
    
    app = ZapretManager(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()