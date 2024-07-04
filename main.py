# Для считывания PDF
import PyPDF2
# Для анализа структуры PDF и извлечения текста
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTRect
# Для извлечения текста из таблиц в PDF
import pdfplumber
import re
# Для записи результатов в json
import json
# Для парсинга главной страницы МИНЮСТа (HTML)
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup

# Ссылка на родительскую страницу реестра
minust_url = str('http://minjust.gov.ru/ru/activity/directions/998/')
# Пробуем скачать родительскую страницу
try:
    minust_page = urlopen(Request(minust_url, headers={"User-Agent": "Mozilla/5.0"}), minust_url.encode('utf-8'))
except:
    print("Error. Minust is not avaible.")
# Записываем данные в объект
minust_html = minust_page.read().decode('utf-8')
# Кидаем все данные в суп(soup)
minust_soup = BeautifulSoup(minust_html, 'html.parser')
# Вытаскиваем нужное из супчика (перевод в str для спокойствия и надёжности)
block_text = str(minust_soup.select("div.page-block-text"))
# Находим 'Реестр иностранных агентов' в том что мы вытащили из супчика
# И получаем опорную координату в строке для поиска ссылки
# P.S. Сделал так потому что в html развёртке сайта все ссылки-заголовки объеденины в один класс
# Сначала идёт href потом название сразу на кирилице
# Пример: href="/uploaded/files/kopiya-reestr-inostrannyih-agentov-12-04-2024.pdf">Реестр иностранных агентов</a></li>
start_id = block_text.find('Реестр иностранных агентов')
# Убираем лишнии символы перед ссылкой (те самые ">Р)(start_index падает на 'Р')
id = start_id - 3
# Создаём пустую строку для хранения ссылки
out_https = str('')
# Конкатенируем строки начиная с id пока find() не может найти "
# Так сделано потому что ссылка начинается содержится в двойных кавычках
# Но кавычку в конце ссылки мы убираем и т.к. мы перебираем начиная с конца
# Мы будем делать цикл пока в out_https не окажется одна " (она соот. будет находится в самом начале ссылки)
while out_https.find('"') == -1:
    out_https += block_text[id]
    id -= 1
    # Предохранитель
    if id == 0: break
# Т.к. наша полученная строка содержит " , которая нам не нужна
# Мы находим индек кавычки и убираем её через срез строки(оставляем все символы ссылки после кавычки)
index_of_mark =  out_https.find('"')
out_https = out_https[:index_of_mark]
# Т.к. на сайте МИНЮСТа ссылка на файл(реестр) обрезана(без протокола и других данных)
# Мы их добавляем заранее в переменную temp_str
temp_str = 'http://minjust.gov.ru'
# Теперь конкатенируем две части нашей ссылки
# P.S. инверсируем(используем для этого срезку) out_https потому что мы шли в цикле while по строке начиная с конца
minust_pdf_url = temp_str + (out_https[::-1])[len(temp_str) + 1:]
# На этом циганские фокусы заканчиваются)
print(minust_pdf_url)

# Здесь производится загрузка и запись реестра на локальное хранилище.
reestr_pdf = 'C:/Users/Max/Desktop/reestr.pdf'
reestr_pdf_data = urlopen(Request(minust_pdf_url, headers={"User-Agent": "Mozilla/5.0"}), minust_url.encode('utf-8'))
reestr_pdf = reestr_pdf_data.read()
local_pdf = open('C:/Users/Max/Desktop/reestr.pdf', 'wb')
local_pdf.write(reestr_pdf)
local_pdf.close()
# Я понимаю, что привязка файлов к местоположению в системе это плохая идея.
# В своё оправдение скажу, что этот код запускался на Yandex Cloud под Linux.
# Всё находилось в родительской директории и указывалось только название самих файлов.


# Находим путь к output.json
output_json_path = "C:/Users/Max/Desktop/output.json"
# Находим путь к PDF
pdf_path = "C:/Users/Max/Desktop/reestr.pdf"
# Массив для ФИО/Названия
arr_names = []
# Массив для ссылок
arr_urls = []

# Шаблон для поиска ссылки
url_pattern = r"(?P<url>https?://[^\s]+)"

# Создаём функцию для извлечения текста
def text_extraction(element):
    # Извлекаем текст из вложенного текстового элемента
    line_text = element.get_text()
    
    # Находим форматы текста
    # Инициализируем список со всеми форматами, встречающимися в строке текста
    line_formats = []
    for text_line in element:
        if isinstance(text_line, LTTextContainer):
            # Итеративно обходим каждый символ в строке текста
            for character in text_line:
                if isinstance(character, LTChar):
                    # Добавляем к символу название шрифта
                    line_formats.append(character.fontname)
                    # Добавляем к символу размер шрифта
                    line_formats.append(character.size)
    # Находим уникальные размеры и названия шрифтов в строке
    format_per_line = list(set(line_formats))
    
    # Возвращаем кортеж с текстом в каждой строке вместе с его форматом
    return (line_text, format_per_line)

# Извлечение таблиц из страницы
def extract_table(pdf_path, page_num, table_num):
    # Открываем файл pdf
    pdf = pdfplumber.open(pdf_path)
    # Находим исследуемую страницу
    table_page = pdf.pages[page_num]
    # Извлекаем соответствующую таблицу
    table = table_page.extract_tables()[table_num]
    return table

# Преобразуем таблицу в соответствующий формат
def table_converter(table):
    table_string = ''
    # Итеративно обходим каждую строку в таблице
    for row_num in range(len(table)):
        row = table[row_num]
        # Удаляем разрыв строки из текста с переносом
        cleaned_row = [item.replace('\n', ' ') if item is not None and '\n' in item else 'None' if item is None else item for item in row]
        # Помещаем найденные имена иноагентов в глобальный массив
        arr_names.append((re.split(",|'", str(cleaned_row)))[4])
        # Ищем ссылки
        url_output = re.findall(url_pattern, str(cleaned_row))
        # Сохраняем ссылки в массиве
        arr_urls.append(str(url_output))
        # Преобразуем таблицу в строку
        table_string+=('|'+'|'.join(cleaned_row)+'|'+'\n')
    # Удаляем последний разрыв строки
    table_string = table_string[:-1]
    return table_string

# Функиция для записи имён и ссылок в json
def write_in_json(arr_names_str, arr_urls_str):
    output_json = open(output_json_path, "w", encoding="utf-16")
    for i in range(len(arr_names_str)):
        data = {
            "title": arr_names_str[i],
            "urls": arr_urls[i]
        }
        json_object = json.dumps(data, indent=4, ensure_ascii=False)
        output_json.write(json_object)

# создаём объект файла PDF
pdfFileObj = open(pdf_path, "rb")
# создаём объект считывателя PDF
pdfReaded = PyPDF2.PdfReader(pdfFileObj)

# Извлекаем страницы из PDF
for pagenum, page in enumerate(extract_pages(pdf_path)):
    
    # Инициализируем переменные, необходимые для извлечения текста со страницы
    pageObj = pdfReaded.pages[pagenum]
    page_text = []
    line_format = []
    text_from_tables = []
    page_content = []
    # Инициализируем количество исследованных таблиц
    table_num = 0
    first_element= True
    table_extraction_flag= False
    # Открываем файл pdf
    pdf = pdfplumber.open(pdf_path)
    # Находим исследуемую страницу
    page_tables = pdf.pages[pagenum]
    # Находим количество таблиц на странице
    tables = page_tables.find_tables()


    # Находим все элементы
    page_elements = [(element.y1, element) for element in page._objs]
    # Сортируем все элементы по порядку нахождения на странице
    page_elements.sort(key=lambda a: a[0], reverse=True)

    # Находим элементы, составляющие страницу
    for i,component in enumerate(page_elements):
        # Извлекаем положение верхнего края элемента в PDF
        pos= component[0]
        # Извлекаем элемент структуры страницы
        element = component[1]

        # Проверяем элементы на наличие таблиц
        if isinstance(element, LTRect):
            # Если первый прямоугольный элемент
            if first_element == True and (table_num+1) <= len(tables):
                # Находим ограничивающий прямоугольник таблицы
                lower_side = page.bbox[3] - tables[table_num].bbox[3]
                upper_side = element.y1
                # Извлекаем информацию из таблицы
                table = extract_table(pdf_path, pagenum, table_num)
                # Преобразуем информацию таблицы в формат структурированной строки
                table_string = table_converter(table)
                # Добавляем строку таблицы в список
                text_from_tables.append(table_string)
                page_content.append(table_string)
                # Устанавливаем флаг True, чтобы избежать повторения содержимого
                table_extraction_flag = True
                # Преобразуем в другой элемент
                first_element = False
                # Добавляем условное обозначение в списки текста и формата
                page_text.append('table')
                line_format.append('table')

            # Проверяем, извлекли ли мы уже таблицы из этой страницы
            if element.y0 >= lower_side and element.y1 <= upper_side:
                pass
            elif not isinstance(page_elements[i][1], LTRect):
                table_extraction_flag = False
                first_element = True
                table_num+=1

# Записываем все имена и ссылки в json
write_in_json(arr_names, arr_urls)

# Закрываем объект файла pdf
pdfFileObj.close()
