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
import shutil

class ZapretGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Zapret Discord YouTube - GUI Controller")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Проверяем права администратора при запуске
        self.is_admin = self.is_admin_user()
        
        # Если нет прав - запрашиваем
        if not self.is_admin:
            self.request_admin_rights()
            return
            
        # Переменные
        self.zapret_path = tk.StringVar()
        self.selected_strategy = tk.StringVar(value="general (ALT).bat")
        self.is_running = False
        self.process = None
        self.winws_pids = []
        
        # Статусы
        self.service_status = tk.StringVar(value="Неизвестно")
        self.game_filter_status = tk.StringVar(value="unknown")
        self.ipset_filter_status = tk.StringVar(value="unknown")
        
        # Список стратегий
        self.strategies = []
        
        # Автоопределение пути
        self.auto_detect_path()
        
        # Настройка UI
        self.setup_ui()
        
        # Обновление списка стратегий
        self.refresh_strategies()
        
        # Запуск мониторинга
        self.start_monitoring()
        
        self.log("✅ Программа запущена с правами администратора")
        self.log(f"📁 Путь: {self.zapret_path.get()}")
        
    def is_admin_user(self):
        """Проверка прав администратора"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
            
    def request_admin_rights(self):
        """Запрос прав администратора через UAC"""
        try:
            # Получаем путь к текущему скрипту
            script = os.path.abspath(sys.argv[0])
            
            # Запускаем с правами администратора
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                f'"{script}"',
                None,
                1
            )
            # Закрываем текущий экземпляр
            self.root.quit()
            sys.exit()
        except Exception as e:
            messagebox.showerror(
                "Ошибка", 
                f"Не удалось получить права администратора!\n\n"
                f"Пожалуйста, запустите программу от имени администратора.\n\n"
                f"Ошибка: {e}"
            )
            sys.exit()
            
    def auto_detect_path(self):
        """Автоматическое определение пути"""
        # Проверяем, где находится скрипт
        script_dir = Path(sys.argv[0]).parent
        
        # Если скрипт в папке gui, поднимаемся на уровень выше
        if script_dir.name == "gui":
            script_dir = script_dir.parent
            
        if (script_dir / "service.bat").exists():
            self.zapret_path.set(str(script_dir))
            return
            
        # Проверяем стандартные пути
        common_paths = [
            "C:\\zapret",
            "C:\\zapret-discord-youtube",
            str(Path.home() / "zapret"),
            str(script_dir)
        ]
        
        for path in common_paths:
            if Path(path).exists() and (Path(path) / "service.bat").exists():
                self.zapret_path.set(path)
                return
                
        # Если ничего не найдено, просим указать вручную
        self.zapret_path.set(str(script_dir))
        
    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Индикатор прав администратора
        admin_frame = ttk.Frame(main_frame)
        admin_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        ttk.Label(admin_frame, text="🔐 Права: АДМИНИСТРАТОР", 
                 foreground="green").pack(side=tk.LEFT)
        
        # 1. Путь к папке
        ttk.Label(main_frame, text="📁 Путь к zapret:").grid(row=1, column=0, sticky=tk.W, pady=5)
        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        path_frame.columnconfigure(0, weight=1)
        
        path_entry = ttk.Entry(path_frame, textvariable=self.zapret_path, width=50)
        path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(path_frame, text="Обзор", command=self.browse_folder).grid(row=0, column=1, padx=5)
        ttk.Button(path_frame, text="🔄", command=self.refresh_strategies).grid(row=0, column=2, padx=2)
        
        # 2. Выбор стратегии
        ttk.Label(main_frame, text="🎯 Стратегия:").grid(row=2, column=0, sticky=tk.W, pady=5)
        strategy_frame = ttk.Frame(main_frame)
        strategy_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        strategy_frame.columnconfigure(0, weight=1)
        
        self.strategy_combo = ttk.Combobox(strategy_frame, textvariable=self.selected_strategy,
                                          state="readonly", width=50)
        self.strategy_combo.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 3. Кнопки управления
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        self.start_btn = ttk.Button(btn_frame, text="▶ Запустить", 
                                   command=self.start_zapret, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Остановить", 
                                  command=self.stop_zapret, state=tk.DISABLED, width=15)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🔄 Перезапустить", 
                  command=self.restart_zapret, width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(btn_frame, text="📦 Установить службу", 
                  command=self.install_service, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑 Удалить службу", 
                  command=self.remove_service, width=15).pack(side=tk.LEFT, padx=5)
        
        # 4. Статус
        status_frame = ttk.LabelFrame(main_frame, text="📊 Статус", padding="10")
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X, expand=True)
        
        left_status = ttk.Frame(status_grid)
        left_status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        right_status = ttk.Frame(status_grid)
        right_status.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Левая колонка
        ttk.Label(left_status, text="Состояние:").grid(row=0, column=0, sticky=tk.W)
        self.status_label = ttk.Label(left_status, text="❌ Не запущен", foreground="red")
        self.status_label.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(left_status, text="PID:").grid(row=1, column=0, sticky=tk.W)
        self.pid_label = ttk.Label(left_status, text="-")
        self.pid_label.grid(row=1, column=1, sticky=tk.W, padx=10)
        
        # Правая колонка
        ttk.Label(right_status, text="Служба:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(right_status, textvariable=self.service_status).grid(row=0, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(right_status, text="Game Filter:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(right_status, textvariable=self.game_filter_status).grid(row=1, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(right_status, text="IPSet Filter:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(right_status, textvariable=self.ipset_filter_status).grid(row=2, column=1, sticky=tk.W, padx=10)
        
        # 5. Дополнительные функции
        extra_frame = ttk.Frame(main_frame)
        extra_frame.grid(row=5, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(extra_frame, text="🔄 Обновить списки", 
                  command=self.update_lists).pack(side=tk.LEFT, padx=5)
        ttk.Button(extra_frame, text="🔍 Диагностика", 
                  command=self.run_diagnostics).pack(side=tk.LEFT, padx=5)
        ttk.Button(extra_frame, text="📝 Обновить hosts", 
                  command=self.update_hosts).pack(side=tk.LEFT, padx=5)
        ttk.Button(extra_frame, text="🔍 Проверить статус", 
                  command=self.check_status).pack(side=tk.LEFT, padx=5)
        
        # Фильтры
        self.game_filter_btn = ttk.Button(extra_frame, text="🎮 GF: неизвестно", 
                                         command=self.toggle_game_filter)
        self.game_filter_btn.pack(side=tk.LEFT, padx=5)
        
        self.ipset_filter_btn = ttk.Button(extra_frame, text="🌐 IF: неизвестно", 
                                          command=self.toggle_ipset_filter)
        self.ipset_filter_btn.pack(side=tk.LEFT, padx=5)
        
        # 6. Лог
        log_frame = ttk.LabelFrame(main_frame, text="📋 Лог", padding="5")
        log_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, 
                                                 state=tk.DISABLED, wrap=tk.WORD,
                                                 font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Кнопки под логом
        log_btn_frame = ttk.Frame(main_frame)
        log_btn_frame.grid(row=7, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(log_btn_frame, text="🗑 Очистить", 
                  command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_btn_frame, text="💾 Сохранить", 
                  command=self.save_log).pack(side=tk.LEFT, padx=5)
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Информация
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(info_frame, text="💡 Запускает BAT-файлы и следит за процессом", 
                 foreground="blue").pack(side=tk.LEFT)
        ttk.Label(info_frame, text="⚡ Все команды выполняются с правами администратора", 
                 foreground="green").pack(side=tk.RIGHT)
        
    def browse_folder(self):
        """Выбор папки"""
        folder = filedialog.askdirectory(title="Выберите папку с zapret-discord-youtube")
        if folder:
            self.zapret_path.set(folder)
            self.refresh_strategies()
            self.log(f"✅ Путь изменен: {folder}")
            
    def refresh_strategies(self):
        """Обновление списка стратегий"""
        path = Path(self.zapret_path.get())
        if not path.exists():
            self.log(f"⚠️ Папка не существует: {path}")
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
            
    def log(self, message):
        """Добавление сообщения в лог"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def clear_log(self):
        """Очистка лога"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def save_log(self):
        """Сохранение лога"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt")]
        )
        if file_path:
            try:
                content = self.log_text.get(1.0, tk.END)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log(f"💾 Лог сохранен: {file_path}")
            except Exception as e:
                self.log(f"❌ Ошибка сохранения: {e}")
                
    # ===== ОСНОВНЫЕ ФУНКЦИИ =====
    
    def start_zapret(self):
        """Запуск стратегии"""
        if self.is_running:
            self.log("⚠️ Уже запущено")
            return
            
        strategy = self.selected_strategy.get()
        strategy_path = Path(self.zapret_path.get()) / strategy
        
        if not strategy_path.exists():
            messagebox.showerror("Ошибка", f"Файл не найден:\n{strategy_path}")
            return
            
        try:
            self.log(f"🚀 Запуск: {strategy}")
            self.progress.start()
            
            # Запускаем BAT-файл
            # Используем ShellExecuteW для запуска с правами админа
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "open",
                str(strategy_path),
                None,
                str(strategy_path.parent),
                1  # SW_SHOWNORMAL
            )
            
            if result <= 32:
                raise Exception(f"Ошибка запуска (код: {result})")
                
            self.is_running = True
            
            # Обновляем UI
            self.status_label.config(text="✅ Запущен", foreground="green")
            self.pid_label.config(text="см. консоль")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            self.log(f"✅ Запущен успешно")
            
            # Проверяем наличие winws.exe через несколько секунд
            self.root.after(3000, self.check_winws)
            
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            messagebox.showerror("Ошибка", str(e))
        finally:
            self.progress.stop()
            
    def check_winws(self):
        """Проверка наличия winws.exe"""
        found_pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'winws.exe' in proc.info['name'].lower():
                    found_pids.append(str(proc.info['pid']))
            except:
                pass
                
        if found_pids:
            self.log(f"✅ Найден winws.exe (PID: {', '.join(found_pids)})")
            self.pid_label.config(text=', '.join(found_pids))
        else:
            self.log("⚠️ winws.exe не найден. Возможно, стратегия не работает")
            
    def stop_zapret(self):
        """Остановка - убиваем все процессы"""
        if not self.is_running:
            self.log("⚠️ Не запущено")
            return
            
        self.log("⏹ Остановка...")
        self.progress.start()
        
        try:
            killed = 0
            
            # 1. Ищем winws.exe
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'winws.exe' in proc.info['name'].lower():
                        proc.kill()
                        killed += 1
                        self.log(f"✅ Завершен winws.exe (PID: {proc.info['pid']})")
                except:
                    pass
                    
            # 2. Ищем cmd.exe с zapret
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'cmd.exe' in proc.info['name'].lower():
                        if proc.info['cmdline']:
                            cmdline = ' '.join(proc.info['cmdline']).lower()
                            if 'general' in cmdline or 'zapret' in cmdline or 'winws' in cmdline:
                                proc.kill()
                                killed += 1
                                self.log(f"✅ Завершена cmd (PID: {proc.info['pid']})")
                except:
                    pass
                    
            # 3. Ищем консольные окна
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'conhost.exe' in proc.info['name'].lower():
                        proc.kill()
                        killed += 1
                except:
                    pass
                    
            self.is_running = False
            self.process = None
            
            self.status_label.config(text="❌ Остановлен", foreground="red")
            self.pid_label.config(text="-")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
            self.log(f"✅ Остановлен. Завершено процессов: {killed}")
            
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
        finally:
            self.progress.stop()
            
    def restart_zapret(self):
        """Перезапуск"""
        self.log("🔄 Перезапуск...")
        if self.is_running:
            self.stop_zapret()
            time.sleep(2)
        self.start_zapret()
        
    def start_monitoring(self):
        """Запуск мониторинга"""
        def monitor():
            while True:
                try:
                    if self.is_running:
                        # Проверяем winws.exe
                        found = False
                        for proc in psutil.process_iter(['name']):
                            try:
                                if proc.info['name'] and 'winws.exe' in proc.info['name'].lower():
                                    found = True
                                    break
                            except:
                                pass
                                
                        if not found:
                            # Проверяем cmd с zapret
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
        """Обработка смерти процесса"""
        if not self.is_running:
            return
            
        self.is_running = False
        self.process = None
        
        self.status_label.config(text="⚠️ Процесс завершен", foreground="orange")
        self.pid_label.config(text="-")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        self.log("⚠️ Процесс завершен (возможно, закрыли консоль)")
        
    # ===== ФУНКЦИИ SERVICE.BAT =====
    
    def run_service_command(self, command):
        """Запуск команды service.bat"""
        service_path = Path(self.zapret_path.get()) / "service.bat"
        if not service_path.exists():
            self.log(f"❌ service.bat не найден")
            return None
            
        try:
            # Запускаем через ShellExecute с правами админа
            cmd = f'"{service_path}" {command}'
            process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=str(self.zapret_path.get()),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='cp866'
            )
            stdout, stderr = process.communicate(timeout=30)
            
            if stdout:
                self.log(f"📤 {stdout[:300]}")
            if stderr:
                self.log(f"⚠️ {stderr[:200]}")
                
            return stdout
            
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            return None
            
    def install_service(self):
        """Установка службы"""
        strategy = self.selected_strategy.get()
        if not messagebox.askyesno("Подтверждение", 
                                  f"Установить службу с '{strategy}'?"):
            return
            
        self.log(f"📦 Установка службы: {strategy}")
        
        # Используем service.bat с параметром 1 (Install Service)
        self.run_service_command("1")
        time.sleep(2)
        self.check_status()
        
    def remove_service(self):
        """Удаление службы"""
        if not messagebox.askyesno("Подтверждение", "Удалить все службы?"):
            return
            
        self.log("🗑 Удаление служб...")
        self.run_service_command("2")
        self.service_status.set("Не установлена")
        self.log("✅ Службы удалены")
        
    def check_status(self):
        """Проверка статуса"""
        self.log("🔍 Проверка статуса...")
        result = self.run_service_command("3")
        
        if result:
            if "Game Filter" in result:
                if "enabled" in result.lower():
                    self.game_filter_status.set("enabled")
                    self.game_filter_btn.config(text="🎮 GF: ENABLED")
                else:
                    self.game_filter_status.set("disabled")
                    self.game_filter_btn.config(text="🎮 GF: DISABLED")
                    
            if "IPSet Filter" in result:
                if "loaded" in result.lower():
                    self.ipset_filter_status.set("loaded")
                elif "any" in result.lower():
                    self.ipset_filter_status.set("any")
                else:
                    self.ipset_filter_status.set("none")
                self.ipset_filter_btn.config(text=f"🌐 IF: {self.ipset_filter_status.get()}")
                
            if "Service" in result:
                if "not" in result.lower():
                    self.service_status.set("Не установлена")
                else:
                    self.service_status.set("Установлена")
                    
    def update_lists(self):
        """Обновление списков"""
        self.log("🔄 Обновление списков...")
        self.run_service_command("8")
        
    def update_hosts(self):
        """Обновление hosts"""
        self.log("📝 Обновление hosts...")
        self.run_service_command("9")
        
    def run_diagnostics(self):
        """Диагностика"""
        self.log("🔍 Диагностика...")
        self.run_service_command("11")
        
    def toggle_game_filter(self):
        """Переключение Game Filter"""
        self.log("🎮 Переключение Game Filter...")
        self.run_service_command("4")
        time.sleep(1)
        self.check_status()
        
    def toggle_ipset_filter(self):
        """Переключение IPSet Filter"""
        self.log("🌐 Переключение IPSet Filter...")
        self.run_service_command("5")
        time.sleep(1)
        self.check_status()
        
    def on_closing(self):
        """Закрытие"""
        if self.is_running:
            if messagebox.askyesno("Подтверждение", "Остановить перед закрытием?"):
                self.stop_zapret()
        self.root.destroy()

def main():
    root = tk.Tk()
    
    # Стиль
    style = ttk.Style()
    style.theme_use('clam')
    
    app = ZapretGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()