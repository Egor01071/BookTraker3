"""
GitHub User Finder - GUI приложение для поиска пользователей GitHub
с возможностью добавления в избранное и сохранения в JSON.

Автор: Студент [Ваше Имя Фамилия]
Дата: Май 2026
Версия: 1.0
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import requests
from PIL import Image, ImageTk
from io import BytesIO
import threading
from datetime import datetime

# ------------------ КЛАСС ДЛЯ РАБОТЫ С ИЗБРАННЫМИ ------------------
class FavoritesManager:
    """Управление избранными пользователями: загрузка, сохранение, добавление, удаление."""
    
    def __init__(self, filename="favorites.json"):
        self.filename = filename
        self.favorites = []
        self.load_favorites()
    
    def load_favorites(self):
        """Загружает избранных пользователей из JSON файла."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.favorites = json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки избранного: {e}")
                self.favorites = []
        else:
            self.favorites = []
    
    def save_favorites(self):
        """Сохраняет избранных пользователей в JSON файл."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения избранного: {e}")
            return False
    
    def is_favorite(self, username):
        """Проверяет, находится ли пользователь в избранном."""
        return any(fav['login'] == username for fav in self.favorites)
    
    def add_favorite(self, user_data):
        """Добавляет пользователя в избранное."""
        if not self.is_favorite(user_data['login']):
            # Добавляем временную метку и сохраняем только нужные поля
            favorite = {
                'login': user_data['login'],
                'avatar_url': user_data['avatar_url'],
                'html_url': user_data['html_url'],
                'added_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.favorites.append(favorite)
            self.save_favorites()
            return True
        return False
    
    def remove_favorite(self, username):
        """Удаляет пользователя из избранного."""
        initial_count = len(self.favorites)
        self.favorites = [fav for fav in self.favorites if fav['login'] != username]
        if len(self.favorites) != initial_count:
            self.save_favorites()
            return True
        return False
    
    def get_favorites(self):
        """Возвращает список избранных пользователей."""
        return self.favorites


# ------------------ КЛАСС ДЛЯ РАБОТЫ С GITHUB API ------------------
class GitHubAPI:
    """Класс для взаимодействия с GitHub API."""
    
    BASE_URL = "https://api.github.com"
    
    @staticmethod
    def search_users(query):
        """
        Поиск пользователей на GitHub по запросу.
        Возвращает список пользователей или None при ошибке.
        """
        if not query or len(query.strip()) == 0:
            return None
        
        url = f"{GitHubAPI.BASE_URL}/search/users"
        params = {'q': query.strip(), 'per_page': 30}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('items', [])
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"Ошибка API: {e}")
            return None
    
    @staticmethod
    def get_user_details(username):
        """
        Получает детальную информацию о пользователе.
        """
        if not username:
            return None
        
        url = f"{GitHubAPI.BASE_URL}/users/{username}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"Ошибка получения данных пользователя: {e}")
            return None


# ------------------ ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ ------------------
class GitHubUserFinder:
    """Главный класс GUI приложения."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub User Finder - Поиск пользователей GitHub")
        self.root.geometry("1100x650")
        self.root.resizable(True, True)
        
        # Инициализация менеджеров
        self.favorites_manager = FavoritesManager()
        self.api = GitHubAPI()
        
        # Переменная для хранения текущих результатов поиска
        self.current_search_results = []
        
        # Кэш для аватаров
        self.avatar_cache = {}
        
        self.create_widgets()
        self.load_favorites_display()
    
    def create_widgets(self):
        """Создание всех элементов интерфейса."""
        # Верхняя панель поиска
        search_frame = ttk.LabelFrame(self.root, text="Поиск пользователей GitHub", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(search_frame, text="Введите имя пользователя:").pack(side=tk.LEFT, padx=5)
        
        self.search_entry = ttk.Entry(search_frame, width=40, font=("Arial", 11))
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", lambda e: self.search_users())
        
        self.search_button = ttk.Button(search_frame, text="🔍 Найти", command=self.search_users)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        # Метка для статуса
        self.status_label = ttk.Label(search_frame, text="Готов к поиску", foreground="gray")
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        # Основная область: таблица результатов и избранное
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Левая часть: результаты поиска
        left_frame = ttk.LabelFrame(main_frame, text="Результаты поиска", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Таблица результатов
        columns = ("Аватар", "Логин", "Тип", "Ссылка на профиль", "Действие")
        self.result_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=20)
        
        self.result_tree.heading("Аватар", text="Аватар")
        self.result_tree.heading("Логин", text="Логин")
        self.result_tree.heading("Тип", text="Тип")
        self.result_tree.heading("Ссылка на профиль", text="Ссылка на профиль")
        self.result_tree.heading("Действие", text="Действие")
        
        self.result_tree.column("Аватар", width=80, anchor="center")
        self.result_tree.column("Логин", width=150)
        self.result_tree.column("Тип", width=100)
        self.result_tree.column("Ссылка на профиль", width=250)
        self.result_tree.column("Действие", width=100, anchor="center")
        
        # Скроллбар для таблицы результатов
        scrollbar_left = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar_left.set)
        
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_left.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Правая часть: избранное
        right_frame = ttk.LabelFrame(main_frame, text="⭐ Избранные пользователи", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Таблица избранных
        fav_columns = ("Логин", "Дата добавления", "Действие")
        self.fav_tree = ttk.Treeview(right_frame, columns=fav_columns, show="headings", height=20)
        
        self.fav_tree.heading("Логин", text="Логин")
        self.fav_tree.heading("Дата добавления", text="Дата добавления")
        self.fav_tree.heading("Действие", text="Действие")
        
        self.fav_tree.column("Логин", width=150)
        self.fav_tree.column("Дата добавления", width=150)
        self.fav_tree.column("Действие", width=100, anchor="center")
        
        scrollbar_right = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.fav_tree.yview)
        self.fav_tree.configure(yscrollcommand=scrollbar_right.set)
        
        self.fav_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_right.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Привязка обработчиков кликов
        self.result_tree.bind("<ButtonRelease-1>", self.on_result_click)
        self.fav_tree.bind("<ButtonRelease-1>", self.on_fav_click)
    
    def search_users(self):
        """Выполняет поиск пользователей через GitHub API."""
        query = self.search_entry.get().strip()
        
        # ВАЛИДАЦИЯ: поле поиска не должно быть пустым
        if not query:
            messagebox.showerror("Ошибка ввода", "Поле поиска не может быть пустым!\nВведите имя пользователя GitHub.")
            return
        
        # Очищаем таблицу результатов
        for row in self.result_tree.get_children():
            self.result_tree.delete(row)
        
        self.current_search_results = []
        self.status_label.config(text="Поиск...", foreground="blue")
        self.search_button.config(state=tk.DISABLED)
        
        # Запускаем поиск в отдельном потоке (чтобы GUI не зависал)
        thread = threading.Thread(target=self._search_thread, args=(query,))
        thread.daemon = True
        thread.start()
    
    def _search_thread(self, query):
        """Поток для выполнения API запроса."""
        users = self.api.search_users(query)
        
        # Обновляем GUI в главном потоке
        self.root.after(0, self._update_search_results, users)
    
    def _update_search_results(self, users):
        """Обновляет таблицу результатов поиска."""
        self.search_button.config(state=tk.NORMAL)
        
        if users is None:
            self.status_label.config(text="Ошибка подключения к GitHub API", foreground="red")
            messagebox.showerror("Ошибка", "Не удалось подключиться к GitHub API.\nПроверьте интернет-соединение.")
            return
        
        if len(users) == 0:
            self.status_label.config(text="Пользователи не найдены", foreground="orange")
            messagebox.showinfo("Результат поиска", "Пользователи не найдены.\nПопробуйте другой запрос.")
            return
        
        self.current_search_results = users
        self.status_label.config(text=f"Найдено пользователей: {len(users)}", foreground="green")
        
        # Загружаем аватары в отдельном потоке
        for user in users:
            self._add_user_to_result_table(user)
    
    def _add_user_to_result_table(self, user):
        """Добавляет пользователя в таблицу результатов."""
        login = user.get('login', 'N/A')
        user_type = user.get('type', 'N/A')
        html_url = user.get('html_url', '#')
        
        # Проверяем, в избранном ли пользователь
        is_fav = self.favorites_manager.is_favorite(login)
        action_text = "⭐ Удалить" if is_fav else "➕ В избранное"
        action_color = "red" if is_fav else "green"
        
        # Вставляем строку
        item_id = self.result_tree.insert("", tk.END, values=(
            "Загрузка...",
            login,
            user_type,
            html_url,
            action_text
        ))
        
        # Загружаем аватар асинхронно
        avatar_url = user.get('avatar_url', '')
        if avatar_url:
            thread = threading.Thread(target=self._load_avatar, args=(item_id, avatar_url, 0))
            thread.daemon = True
            thread.start()
    
    def _load_avatar(self, item_id, avatar_url, retry_count):
        """Загружает аватар пользователя."""
        try:
            # Проверяем кэш
            if avatar_url in self.avatar_cache:
                photo = self.avatar_cache[avatar_url]
                self.root.after(0, self._update_avatar, item_id, photo)
                return
            
            response = requests.get(avatar_url, timeout=5)
            if response.status_code == 200:
                img_data = response.content
                img = Image.open(BytesIO(img_data))
                img = img.resize((50, 50), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                # Сохраняем в кэш
                self.avatar_cache[avatar_url] = photo
                
                self.root.after(0, self._update_avatar, item_id, photo)
            else:
                self.root.after(0, self._update_avatar, item_id, None)
        except Exception as e:
            if retry_count < 2:
                # Повторная попытка через 1 секунду
                self.root.after(1000, lambda: self._load_avatar(item_id, avatar_url, retry_count + 1))
            else:
                self.root.after(0, self._update_avatar, item_id, None)
    
    def _update_avatar(self, item_id, photo):
        """Обновляет аватар в таблице."""
        if photo:
            self.result_tree.set(item_id, column="Аватар", value="✅")
            # Сохраняем фото для отображения (Tkinter требует удержания ссылки)
            if not hasattr(self, '_avatar_refs'):
                self._avatar_refs = {}
            self._avatar_refs[item_id] = photo
        else:
            self.result_tree.set(item_id, column="Аватар", value="❌")
    
    def on_result_click(self, event):
        """Обработчик клика по таблице результатов."""
        region = self.result_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        column = self.result_tree.identify_column(event.x)
        if column == "#5":  # Колонка Действие
            item = self.result_tree.selection()[0] if self.result_tree.selection() else self.result_tree.identify_row(event.y)
            if item:
                login = self.result_tree.item(item, "values")[1]
                action = self.result_tree.item(item, "values")[4]
                
                if "В избранное" in action:
                    self._add_to_favorites(login)
                elif "Удалить" in action:
                    self._remove_from_favorites(login)
        elif column == "#4":  # Колонка Ссылка, открываем в браузере
            item = self.result_tree.selection()[0] if self.result_tree.selection() else self.result_tree.identify_row(event.y)
            if item:
                url = self.result_tree.item(item, "values")[3]
                if url and url != "#":
                    import webbrowser
                    webbrowser.open(url)
    
    def _add_to_favorites(self, login):
        """Добавляет пользователя в избранное."""
        # Находим полные данные пользователя
        user_data = None
        for user in self.current_search_results:
            if user.get('login') == login:
                user_data = user
                break
        
        if user_data and self.favorites_manager.add_favorite(user_data):
            self.load_favorites_display()
            self.refresh_actions_in_results()
            messagebox.showinfo("Успех", f"Пользователь {login} добавлен в избранное!")
        else:
            messagebox.showinfo("Информация", f"Пользователь {login} уже в избранном.")
    
    def _remove_from_favorites(self, login):
        """Удаляет пользователя из избранного."""
        if self.favorites_manager.remove_favorite(login):
            self.load_favorites_display()
            self.refresh_actions_in_results()
            messagebox.showinfo("Успех", f"Пользователь {login} удален из избранного!")
    
    def refresh_actions_in_results(self):
        """Обновляет кнопки действий в таблице результатов."""
        for item in self.result_tree.get_children():
            login = self.result_tree.item(item, "values")[1]
            is_fav = self.favorites_manager.is_favorite(login)
            action_text = "⭐ Удалить" if is_fav else "➕ В избранное"
            self.result_tree.set(item, column="Действие", value=action_text)
    
    def load_favorites_display(self):
        """Загружает и отображает избранных пользователей."""
        # Очищаем таблицу избранных
        for row in self.fav_tree.get_children():
            self.fav_tree.delete(row)
        
        favorites = self.favorites_manager.get_favorites()
        
        for fav in favorites:
            self.fav_tree.insert("", tk.END, values=(
                fav['login'],
                fav.get('added_at', 'Дата неизвестна'),
                "❌ Удалить"
            ))
    
    def on_fav_click(self, event):
        """Обработчик клика по таблице избранных."""
        region = self.fav_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        column = self.fav_tree.identify_column(event.x)
        if column == "#3":  # Колонка Действие
            item = self.fav_tree.selection()[0] if self.fav_tree.selection() else self.fav_tree.identify_row(event.y)
            if item:
                login = self.fav_tree.item(item, "values")[0]
                self._remove_from_favorites(login)


# ------------------ ЗАПУСК ПРИЛОЖЕНИЯ ------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubUserFinder(root)
    root.mainloop()
