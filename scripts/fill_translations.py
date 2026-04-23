#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fill translation strings into .ts XML files for all target languages.
Run from project root: .venv/bin/python scripts/fill_translations.py
"""

import copy
import os
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Translation tables
# source string -> {lang_code: translation}
# ---------------------------------------------------------------------------
T: dict[str, dict[str, str]] = {

    # ── Icons ──────────────────────────────────────────────────────────────
    "Phone":            {"de": "Telefon",       "es": "Teléfono",       "fr": "Téléphone",      "ja": "電話",           "pt_BR": "Telefone",        "ru": "Телефон",            "zh_CN": "电话"},
    "Mobile":           {"de": "Mobiltelefon",  "es": "Móvil",          "fr": "Portable",       "ja": "携帯電話",        "pt_BR": "Celular",         "ru": "Мобильный",          "zh_CN": "手机"},
    "Fax":              {"de": "Fax",           "es": "Fax",            "fr": "Fax",            "ja": "ファックス",      "pt_BR": "Fax",             "ru": "Факс",               "zh_CN": "传真"},
    "E-Mail":           {"de": "E-Mail",        "es": "Correo electrónico", "fr": "E-mail",     "ja": "メール",          "pt_BR": "E-mail",          "ru": "Эл. почта",          "zh_CN": "电子邮件"},
    "Website":          {"de": "Website",       "es": "Sitio web",      "fr": "Site web",       "ja": "ウェブサイト",    "pt_BR": "Website",         "ru": "Веб-сайт",           "zh_CN": "网站"},
    "Location":         {"de": "Standort",      "es": "Ubicación",      "fr": "Adresse",        "ja": "所在地",          "pt_BR": "Endereço",        "ru": "Адрес",              "zh_CN": "地址"},
    "Person":           {"de": "Person",        "es": "Persona",        "fr": "Personne",       "ja": "人物",           "pt_BR": "Pessoa",          "ru": "Персона",            "zh_CN": "人员"},
    "Company":          {"de": "Unternehmen",   "es": "Empresa",        "fr": "Entreprise",     "ja": "会社",           "pt_BR": "Empresa",         "ru": "Компания",           "zh_CN": "公司"},
    "Time":             {"de": "Uhrzeit",       "es": "Hora",           "fr": "Horaires",       "ja": "営業時間",        "pt_BR": "Horário",         "ru": "Время",              "zh_CN": "时间"},
    "Printer":          {"de": "Drucker",       "es": "Impresora",      "fr": "Imprimante",     "ja": "プリンター",      "pt_BR": "Impressora",      "ru": "Принтер",            "zh_CN": "打印机"},
    "Link":             {"de": "Link",          "es": "Enlace",         "fr": "Lien",           "ja": "リンク",          "pt_BR": "Link",            "ru": "Ссылка",             "zh_CN": "链接"},
    "@ (E-Mail)":       {"de": "@ (E-Mail)",   "es": "@ (Correo)",     "fr": "@ (E-mail)",     "ja": "@ (メール)",      "pt_BR": "@ (E-mail)",      "ru": "@ (Эл. почта)",      "zh_CN": "@ (邮件)"},

    # ── Paper size presets ─────────────────────────────────────────────────
    "A4 Portrait":      {"de": "A4 Hochformat",     "es": "A4 vertical",        "fr": "A4 portrait",        "ja": "A4 縦",      "pt_BR": "A4 retrato",      "ru": "A4 книжная",         "zh_CN": "A4 纵向"},
    "A4 Landscape":     {"de": "A4 Querformat",     "es": "A4 horizontal",      "fr": "A4 paysage",         "ja": "A4 横",      "pt_BR": "A4 paisagem",     "ru": "A4 альбомная",       "zh_CN": "A4 横向"},
    "A5 Portrait":      {"de": "A5 Hochformat",     "es": "A5 vertical",        "fr": "A5 portrait",        "ja": "A5 縦",      "pt_BR": "A5 retrato",      "ru": "A5 книжная",         "zh_CN": "A5 纵向"},
    "A5 Landscape":     {"de": "A5 Querformat",     "es": "A5 horizontal",      "fr": "A5 paysage",         "ja": "A5 横",      "pt_BR": "A5 paisagem",     "ru": "A5 альбомная",       "zh_CN": "A5 横向"},
    "Letter Portrait":  {"de": "Letter Hochformat", "es": "Carta vertical",     "fr": "Lettre portrait",    "ja": "レター 縦",  "pt_BR": "Carta retrato",   "ru": "Letter книжная",     "zh_CN": "Letter 纵向"},
    "Letter Landscape": {"de": "Letter Querformat", "es": "Carta horizontal",   "fr": "Lettre paysage",     "ja": "レター 横",  "pt_BR": "Carta paisagem",  "ru": "Letter альбомная",   "zh_CN": "Letter 横向"},
    "Custom":           {"de": "Benutzerdefiniert", "es": "Personalizado",      "fr": "Personnalisé",       "ja": "カスタム",   "pt_BR": "Personalizado",   "ru": "Произвольный",       "zh_CN": "自定义"},

    # ── IconPickerDialog ───────────────────────────────────────────────────
    "Choose Icon":      {"de": "Symbol wählen",     "es": "Elegir icono",       "fr": "Choisir une icône",  "ja": "アイコンを選択", "pt_BR": "Escolher ícone", "ru": "Выбрать значок",    "zh_CN": "选择图标"},

    # ── MailMergeDialog ────────────────────────────────────────────────────
    "Mail Merge":                                   {"de": "Serienbrief",               "es": "Combinación de correspondencia", "fr": "Publipostage",           "ja": "差し込み印刷",       "pt_BR": "Mala direta",             "ru": "Серийное письмо",        "zh_CN": "邮件合并"},
    "Data Source":                                  {"de": "Datenquelle",               "es": "Fuente de datos",                "fr": "Source de données",      "ja": "データソース",       "pt_BR": "Fonte de dados",          "ru": "Источник данных",        "zh_CN": "数据源"},
    "No file loaded":                               {"de": "Keine Datei geladen",        "es": "Sin archivo cargado",            "fr": "Aucun fichier chargé",   "ja": "ファイル未読み込み", "pt_BR": "Nenhum arquivo carregado","ru": "Файл не загружен",        "zh_CN": "未加载文件"},
    "Open CSV/Excel…":                              {"de": "CSV/Excel öffnen …",         "es": "Abrir CSV/Excel…",               "fr": "Ouvrir CSV/Excel…",      "ja": "CSV/Excelを開く…",   "pt_BR": "Abrir CSV/Excel…",        "ru": "Открыть CSV/Excel…",     "zh_CN": "打开 CSV/Excel…"},
    "Data Preview":                                 {"de": "Datenvorschau",              "es": "Vista previa de datos",          "fr": "Aperçu des données",     "ja": "データプレビュー",   "pt_BR": "Pré-visualização",        "ru": "Предпросмотр данных",    "zh_CN": "数据预览"},
    "Available Placeholders (use in text elements)":{"de": "Verfügbare Platzhalter (in Textelemente einfügen)", "es": "Marcadores disponibles (usar en elementos de texto)", "fr": "Espaces réservés disponibles (à insérer dans les éléments texte)", "ja": "使用可能なプレースホルダー（テキスト要素で使用）", "pt_BR": "Variáveis disponíveis (inserir em elementos de texto)", "ru": "Доступные поля (вставлять в текстовые элементы)", "zh_CN": "可用占位符（用于文本元素）"},
    "Generate Cards":                               {"de": "Karten erzeugen",            "es": "Generar tarjetas",               "fr": "Générer les cartes",     "ja": "カードを生成",       "pt_BR": "Gerar cartões",           "ru": "Создать карточки",       "zh_CN": "生成名片"},
    "Open File":                                    {"de": "Datei öffnen",               "es": "Abrir archivo",                  "fr": "Ouvrir un fichier",      "ja": "ファイルを開く",     "pt_BR": "Abrir arquivo",           "ru": "Открыть файл",           "zh_CN": "打开文件"},
    "Spreadsheets (*.csv *.xlsx *.xls)":            {"de": "Tabellen (*.csv *.xlsx *.xls)", "es": "Hojas de cálculo (*.csv *.xlsx *.xls)", "fr": "Tableurs (*.csv *.xlsx *.xls)", "ja": "表計算ファイル (*.csv *.xlsx *.xls)", "pt_BR": "Planilhas (*.csv *.xlsx *.xls)", "ru": "Таблицы (*.csv *.xlsx *.xls)", "zh_CN": "电子表格 (*.csv *.xlsx *.xls)"},
    "Error":                                        {"de": "Fehler",                     "es": "Error",                          "fr": "Erreur",                 "ja": "エラー",             "pt_BR": "Erro",                    "ru": "Ошибка",                 "zh_CN": "错误"},
    "No Data":                                      {"de": "Keine Daten",                "es": "Sin datos",                      "fr": "Aucune donnée",          "ja": "データなし",         "pt_BR": "Sem dados",               "ru": "Нет данных",             "zh_CN": "无数据"},
    "Please load a file first.":                    {"de": "Bitte zuerst eine Datei laden.", "es": "Por favor, cargue primero un archivo.", "fr": "Veuillez d'abord charger un fichier.", "ja": "最初にファイルを読み込んでください。", "pt_BR": "Por favor, carregue um arquivo primeiro.", "ru": "Сначала загрузите файл.", "zh_CN": "请先加载文件。"},

    # ── MainWindow -- side buttons ──────────────────────────────────────────
    "Front":            {"de": "Vorderseite",   "es": "Anverso",        "fr": "Recto",          "ja": "表面",           "pt_BR": "Frente",          "ru": "Лицевая сторона",    "zh_CN": "正面"},
    "Back":             {"de": "Rückseite",     "es": "Reverso",        "fr": "Verso",          "ja": "裏面",           "pt_BR": "Verso",           "ru": "Обратная сторона",   "zh_CN": "背面"},

    # ── MainWindow -- section labels ────────────────────────────────────────
    "CARDS":            {"de": "KARTEN",        "es": "TARJETAS",       "fr": "CARTES",         "ja": "カード",          "pt_BR": "CARTÕES",         "ru": "КАРТОЧКИ",           "zh_CN": "名片"},
    "VIEW":             {"de": "ANSICHT",        "es": "VISTA",          "fr": "AFFICHAGE",      "ja": "表示",           "pt_BR": "VISUALIZAÇÃO",    "ru": "ВИД",                "zh_CN": "视图"},

    # ── MainWindow -- card/element panel ───────────────────────────────────
    "Cards:":                           {"de": "Karten:",               "es": "Tarjetas:",          "fr": "Cartes :",               "ja": "カード：",       "pt_BR": "Cartões:",            "ru": "Карточки:",              "zh_CN": "名片："},
    "Add new card":                     {"de": "Neue Karte hinzufügen", "es": "Añadir nueva tarjeta","fr": "Ajouter une carte",      "ja": "カードを追加",   "pt_BR": "Adicionar novo cartão","ru": "Добавить карточку",      "zh_CN": "添加名片"},
    "Duplicate current card":           {"de": "Aktuelle Karte duplizieren","es": "Duplicar tarjeta actual","fr": "Dupliquer la carte","ja": "カードを複製",  "pt_BR": "Duplicar cartão atual","ru": "Дублировать карточку",   "zh_CN": "复制当前名片"},
    "Rename card":                      {"de": "Karte umbenennen",      "es": "Renombrar tarjeta",  "fr": "Renommer la carte",      "ja": "カード名を変更", "pt_BR": "Renomear cartão",      "ru": "Переименовать карточку", "zh_CN": "重命名名片"},
    "Delete card":                      {"de": "Karte löschen",         "es": "Eliminar tarjeta",   "fr": "Supprimer la carte",     "ja": "カードを削除",   "pt_BR": "Excluir cartão",       "ru": "Удалить карточку",       "zh_CN": "删除名片"},
    "Layer:":                           {"de": "Ebene:",                "es": "Capa:",              "fr": "Calque :",               "ja": "レイヤー：",     "pt_BR": "Camada:",             "ru": "Слой:",                  "zh_CN": "图层："},
    "Bring element to front (higher layer)": {"de": "Element nach vorne (höhere Ebene)", "es": "Traer al frente (capa superior)", "fr": "Mettre au premier plan", "ja": "前面へ移動（上位レイヤー）", "pt_BR": "Trazer para frente", "ru": "На передний план", "zh_CN": "上移一层"},
    "Send element to back (lower layer)":    {"de": "Element nach hinten (niedrigere Ebene)", "es": "Enviar al fondo (capa inferior)", "fr": "Mettre en arrière-plan", "ja": "背面へ移動（下位レイヤー）", "pt_BR": "Enviar para trás", "ru": "На задний план", "zh_CN": "下移一层"},
    "Delete selected elements":         {"de": "Ausgewählte Elemente löschen", "es": "Eliminar elementos seleccionados", "fr": "Supprimer les éléments sélectionnés", "ja": "選択した要素を削除", "pt_BR": "Excluir elementos selecionados", "ru": "Удалить выбранные элементы", "zh_CN": "删除所选元素"},
    "Fit to content (text/image/QR)":   {"de": "An Inhalt anpassen (Text/Bild/QR)", "es": "Ajustar al contenido (texto/imagen/QR)", "fr": "Adapter au contenu (texte/image/QR)", "ja": "コンテンツに合わせる（テキスト/画像/QR）", "pt_BR": "Ajustar ao conteúdo (texto/imagem/QR)", "ru": "По размеру содержимого (текст/изображение/QR)", "zh_CN": "适应内容（文字/图片/QR）"},

    # ── MainWindow -- view panel ────────────────────────────────────────────
    "Zoom":             {"de": "Zoom",          "es": "Zoom",           "fr": "Zoom",           "ja": "ズーム",          "pt_BR": "Zoom",            "ru": "Масштаб",            "zh_CN": "缩放"},
    "Grid":             {"de": "Raster",        "es": "Cuadrícula",     "fr": "Grille",         "ja": "グリッド",        "pt_BR": "Grade",           "ru": "Сетка",              "zh_CN": "网格"},
    "Snap":             {"de": "Einrasten",     "es": "Ajuste",         "fr": "Magnétisme",     "ja": "スナップ",        "pt_BR": "Alinhar",         "ru": "Привязка",           "zh_CN": "对齐"},
    "Background":       {"de": "Hintergrund",   "es": "Fondo",          "fr": "Arrière-plan",   "ja": "背景",           "pt_BR": "Plano de fundo",  "ru": "Фон",                "zh_CN": "背景"},
    "Paper template:":  {"de": "Druckvorlage:", "es": "Plantilla de papel:", "fr": "Format d'impression :", "ja": "用紙テンプレート：", "pt_BR": "Modelo de papel:", "ru": "Шаблон листа:", "zh_CN": "纸张模板："},
    "✎ Edit":           {"de": "✎ Bearbeiten",  "es": "✎ Editar",       "fr": "✎ Modifier",     "ja": "✎ 編集",          "pt_BR": "✎ Editar",        "ru": "✎ Изменить",         "zh_CN": "✎ 编辑"},
    "Ready":            {"de": "Bereit",        "es": "Listo",          "fr": "Prêt",           "ja": "準備完了",        "pt_BR": "Pronto",          "ru": "Готово",             "zh_CN": "就绪"},
    "Palette:":         {"de": "Farbpalette:",  "es": "Paleta:",        "fr": "Palette :",      "ja": "カラーパレット：", "pt_BR": "Paleta:",         "ru": "Палитра:",           "zh_CN": "调色板："},
    "Add color to palette": {"de": "Farbe zur Palette hinzufügen", "es": "Añadir color a la paleta", "fr": "Ajouter une couleur à la palette", "ja": "カラーパレットに追加", "pt_BR": "Adicionar cor à paleta", "ru": "Добавить цвет в палитру", "zh_CN": "添加颜色到调色板"},

    # ── MainWindow -- menu bar ──────────────────────────────────────────────
    "&File":                {"de": "&Datei",            "es": "&Archivo",           "fr": "&Fichier",           "ja": "ファイル(&F)",    "pt_BR": "&Arquivo",            "ru": "&Файл",              "zh_CN": "文件(&F)"},
    "New Project":          {"de": "Neues Projekt",     "es": "Nuevo proyecto",     "fr": "Nouveau projet",     "ja": "新規プロジェクト","pt_BR": "Novo projeto",        "ru": "Новый проект",       "zh_CN": "新建项目"},
    "Open…":                {"de": "Öffnen …",          "es": "Abrir…",             "fr": "Ouvrir…",            "ja": "開く…",           "pt_BR": "Abrir…",              "ru": "Открыть…",           "zh_CN": "打开…"},
    "Recent Files":         {"de": "Zuletzt geöffnet",  "es": "Archivos recientes", "fr": "Fichiers récents",   "ja": "最近使ったファイル","pt_BR": "Arquivos recentes",   "ru": "Последние файлы",    "zh_CN": "最近文件"},
    "Save":                 {"de": "Speichern",         "es": "Guardar",            "fr": "Enregistrer",        "ja": "保存",           "pt_BR": "Salvar",              "ru": "Сохранить",          "zh_CN": "保存"},
    "Save As…":             {"de": "Speichern unter …", "es": "Guardar como…",      "fr": "Enregistrer sous…",  "ja": "別名で保存…",     "pt_BR": "Salvar como…",        "ru": "Сохранить как…",     "zh_CN": "另存为…"},
    "Export as Template…":  {"de": "Als Vorlage exportieren …", "es": "Exportar como plantilla…", "fr": "Exporter comme modèle…", "ja": "テンプレートとしてエクスポート…", "pt_BR": "Exportar como modelo…", "ru": "Экспорт как шаблон…", "zh_CN": "导出为模板…"},
    "Import Template…":     {"de": "Vorlage importieren …", "es": "Importar plantilla…", "fr": "Importer un modèle…", "ja": "テンプレートをインポート…", "pt_BR": "Importar modelo…", "ru": "Импортировать шаблон…", "zh_CN": "导入模板…"},
    "Print Preview…":       {"de": "Druckvorschau …",  "es": "Vista previa de impresión…", "fr": "Aperçu avant impression…", "ja": "印刷プレビュー…", "pt_BR": "Visualizar impressão…", "ru": "Предпросмотр печати…", "zh_CN": "打印预览…"},
    "Export PDF / Print…":  {"de": "PDF exportieren / Drucken …", "es": "Exportar PDF / Imprimir…", "fr": "Exporter PDF / Imprimer…", "ja": "PDF出力 / 印刷…", "pt_BR": "Exportar PDF / Imprimir…", "ru": "Экспорт PDF / Печать…", "zh_CN": "导出 PDF / 打印…"},
    "Quit":                 {"de": "Beenden",           "es": "Salir",              "fr": "Quitter",            "ja": "終了",           "pt_BR": "Sair",                "ru": "Выход",              "zh_CN": "退出"},

    "&Edit":                {"de": "&Bearbeiten",       "es": "&Editar",            "fr": "&Édition",           "ja": "編集(&E)",        "pt_BR": "&Editar",             "ru": "&Правка",            "zh_CN": "编辑(&E)"},
    "Undo":                 {"de": "Rückgängig",        "es": "Deshacer",           "fr": "Annuler",            "ja": "元に戻す",        "pt_BR": "Desfazer",            "ru": "Отменить",           "zh_CN": "撤销"},
    "Redo":                 {"de": "Wiederholen",       "es": "Rehacer",            "fr": "Rétablir",           "ja": "やり直し",        "pt_BR": "Refazer",             "ru": "Повторить",          "zh_CN": "重做"},
    "Select All":           {"de": "Alles auswählen",   "es": "Seleccionar todo",   "fr": "Tout sélectionner",  "ja": "すべて選択",      "pt_BR": "Selecionar tudo",     "ru": "Выбрать всё",        "zh_CN": "全选"},
    "Delete Selected":      {"de": "Auswahl löschen",   "es": "Eliminar selección", "fr": "Supprimer la sélection", "ja": "選択削除",   "pt_BR": "Excluir seleção",     "ru": "Удалить выбранное",  "zh_CN": "删除所选"},

    "&Insert":              {"de": "&Einfügen",         "es": "&Insertar",          "fr": "&Insérer",           "ja": "挿入(&I)",        "pt_BR": "&Inserir",            "ru": "&Вставка",           "zh_CN": "插入(&I)"},
    "Text":                 {"de": "Text",              "es": "Texto",              "fr": "Texte",              "ja": "テキスト",        "pt_BR": "Texto",               "ru": "Текст",              "zh_CN": "文字"},
    "Image…":               {"de": "Bild …",            "es": "Imagen…",            "fr": "Image…",             "ja": "画像…",           "pt_BR": "Imagem…",             "ru": "Изображение…",       "zh_CN": "图片…"},
    "Rectangle":            {"de": "Rechteck",          "es": "Rectángulo",         "fr": "Rectangle",          "ja": "長方形",          "pt_BR": "Retângulo",           "ru": "Прямоугольник",      "zh_CN": "矩形"},
    "Ellipse":              {"de": "Ellipse",           "es": "Elipse",             "fr": "Ellipse",            "ja": "楕円",           "pt_BR": "Elipse",              "ru": "Эллипс",             "zh_CN": "椭圆"},
    "Line":                 {"de": "Linie",             "es": "Línea",              "fr": "Ligne",              "ja": "直線",           "pt_BR": "Linha",               "ru": "Линия",              "zh_CN": "直线"},
    "QR Code":              {"de": "QR-Code",           "es": "Código QR",          "fr": "Code QR",            "ja": "QRコード",        "pt_BR": "Código QR",           "ru": "QR-код",             "zh_CN": "二维码"},
    "Icon…":                {"de": "Symbol …",          "es": "Icono…",             "fr": "Icône…",             "ja": "アイコン…",       "pt_BR": "Ícone…",              "ru": "Значок…",            "zh_CN": "图标…"},

    "&Align":               {"de": "&Ausrichten",       "es": "&Alinear",           "fr": "&Aligner",           "ja": "整列(&A)",        "pt_BR": "&Alinhar",            "ru": "&Выравнивание",      "zh_CN": "对齐(&A)"},
    "Left (Card)":          {"de": "Links (Karte)",     "es": "Izquierda (tarjeta)","fr": "Gauche (carte)",     "ja": "左揃え（カード）","pt_BR": "Esquerda (cartão)",   "ru": "По левому краю (карта)", "zh_CN": "左对齐（名片）"},
    "Right (Card)":         {"de": "Rechts (Karte)",    "es": "Derecha (tarjeta)",  "fr": "Droite (carte)",     "ja": "右揃え（カード）","pt_BR": "Direita (cartão)",    "ru": "По правому краю (карта)", "zh_CN": "右对齐（名片）"},
    "Top (Card)":           {"de": "Oben (Karte)",      "es": "Arriba (tarjeta)",   "fr": "Haut (carte)",       "ja": "上揃え（カード）","pt_BR": "Superior (cartão)",   "ru": "По верхнему краю (карта)", "zh_CN": "顶部对齐（名片）"},
    "Bottom (Card)":        {"de": "Unten (Karte)",     "es": "Abajo (tarjeta)",    "fr": "Bas (carte)",        "ja": "下揃え（カード）","pt_BR": "Inferior (cartão)",   "ru": "По нижнему краю (карта)", "zh_CN": "底部对齐（名片）"},
    "Center H":             {"de": "Horizontal zentrieren", "es": "Centrar horizontalmente", "fr": "Centrer horizontalement", "ja": "水平方向に中央揃え", "pt_BR": "Centralizar horizontalmente", "ru": "По центру горизонтально", "zh_CN": "水平居中"},
    "Center V":             {"de": "Vertikal zentrieren", "es": "Centrar verticalmente", "fr": "Centrer verticalement", "ja": "垂直方向に中央揃え", "pt_BR": "Centralizar verticalmente", "ru": "По центру вертикально", "zh_CN": "垂直居中"},
    "Group Left":           {"de": "Gruppe links",      "es": "Grupo izquierda",    "fr": "Groupe gauche",      "ja": "グループ左揃え",  "pt_BR": "Grupo esquerda",      "ru": "Группа по левому краю", "zh_CN": "组左对齐"},
    "Group Right":          {"de": "Gruppe rechts",     "es": "Grupo derecha",      "fr": "Groupe droite",      "ja": "グループ右揃え",  "pt_BR": "Grupo direita",       "ru": "Группа по правому краю", "zh_CN": "组右对齐"},
    "Group Top":            {"de": "Gruppe oben",       "es": "Grupo arriba",       "fr": "Groupe haut",        "ja": "グループ上揃え",  "pt_BR": "Grupo superior",      "ru": "Группа по верхнему краю", "zh_CN": "组顶部对齐"},
    "Group Bottom":         {"de": "Gruppe unten",      "es": "Grupo abajo",        "fr": "Groupe bas",         "ja": "グループ下揃え",  "pt_BR": "Grupo inferior",      "ru": "Группа по нижнему краю", "zh_CN": "组底部对齐"},
    "Group Center H":       {"de": "Gruppe horiz. zentrieren", "es": "Grupo centrar horizontalmente", "fr": "Groupe centrer horiz.", "ja": "グループ水平中央揃え", "pt_BR": "Grupo centralizar horiz.", "ru": "Группа по центру гориз.", "zh_CN": "组水平居中"},
    "Group Center V":       {"de": "Gruppe vertikal zentrieren", "es": "Grupo centrar verticalmente", "fr": "Groupe centrer vert.", "ja": "グループ垂直中央揃え", "pt_BR": "Grupo centralizar vert.", "ru": "Группа по центру верт.", "zh_CN": "组垂直居中"},
    "Distribute Horizontally": {"de": "Horizontal verteilen", "es": "Distribuir horizontalmente", "fr": "Distribuer horizontalement", "ja": "水平方向に分布", "pt_BR": "Distribuir horizontalmente", "ru": "Распределить горизонтально", "zh_CN": "水平分布"},
    "Distribute Vertically":   {"de": "Vertikal verteilen",   "es": "Distribuir verticalmente",   "fr": "Distribuer verticalement",   "ja": "垂直方向に分布", "pt_BR": "Distribuir verticalmente",   "ru": "Распределить вертикально",   "zh_CN": "垂直分布"},

    "Paper &Template":      {"de": "Druckvor&lage",         "es": "Plantilla de &papel",    "fr": "&Format d'impression",   "ja": "用紙テンプレート(&T)", "pt_BR": "&Modelo de papel",    "ru": "&Шаблон листа",          "zh_CN": "纸张模板(&T)"},
    "Edit…":                {"de": "Bearbeiten …",          "es": "Editar…",                "fr": "Modifier…",              "ja": "編集…",               "pt_BR": "Editar…",             "ru": "Изменить…",              "zh_CN": "编辑…"},
    "Manage Library…":      {"de": "Bibliothek verwalten …","es": "Gestionar biblioteca…",  "fr": "Gérer la bibliothèque…", "ja": "ライブラリを管理…",   "pt_BR": "Gerenciar biblioteca…","ru": "Управление библиотекой…","zh_CN": "管理库…"},
    "Save as Template to Library": {"de": "Als Vorlage in Bibliothek speichern", "es": "Guardar como plantilla en biblioteca", "fr": "Enregistrer comme modèle dans la bibliothèque", "ja": "テンプレートとしてライブラリに保存", "pt_BR": "Salvar como modelo na biblioteca", "ru": "Сохранить как шаблон в библиотеку", "zh_CN": "另存为模板到库"},

    "E&xtras":              {"de": "E&xtras",           "es": "E&xtras",            "fr": "E&xtras",            "ja": "その他(&X)",      "pt_BR": "E&xtras",             "ru": "Доп. функции(&X)",   "zh_CN": "附加功能(&X)"},
    "Add Font…":            {"de": "Schrift hinzufügen …","es": "Añadir fuente…",   "fr": "Ajouter une police…","ja": "フォントを追加…", "pt_BR": "Adicionar fonte…",    "ru": "Добавить шрифт…",    "zh_CN": "添加字体…"},
    "Mail Merge…":          {"de": "Serienbrief …",     "es": "Combinación de correspondencia…","fr": "Publipostage…","ja": "差し込み印刷…", "pt_BR": "Mala direta…",       "ru": "Серийное письмо…",   "zh_CN": "邮件合并…"},
    "Appearance":           {"de": "Erscheinungsbild",  "es": "Apariencia",         "fr": "Apparence",          "ja": "外観",           "pt_BR": "Aparência",           "ru": "Оформление",         "zh_CN": "外观"},
    "System (Default)":     {"de": "System (Standard)", "es": "Sistema (predeterminado)","fr": "Système (défaut)", "ja": "システム（デフォルト）","pt_BR": "Sistema (padrão)","ru": "Системная (по умолчанию)","zh_CN": "系统（默认）"},
    "Dark":                 {"de": "Dunkel",            "es": "Oscuro",             "fr": "Sombre",             "ja": "ダーク",          "pt_BR": "Escuro",              "ru": "Тёмная",             "zh_CN": "深色"},
    "Light":                {"de": "Hell",              "es": "Claro",              "fr": "Clair",              "ja": "ライト",          "pt_BR": "Claro",               "ru": "Светлая",            "zh_CN": "浅色"},
    "Language":             {"de": "Sprache",           "es": "Idioma",             "fr": "Langue",             "ja": "言語",           "pt_BR": "Idioma",              "ru": "Язык",               "zh_CN": "语言"},

    # ── MainWindow -- toolbar ───────────────────────────────────────────────
    "Elements":             {"de": "Elemente",          "es": "Elementos",          "fr": "Éléments",           "ja": "要素",           "pt_BR": "Elementos",           "ru": "Элементы",           "zh_CN": "元素"},
    "T Text":               {"de": "T Text",            "es": "T Texto",            "fr": "T Texte",            "ja": "T テキスト",      "pt_BR": "T Texto",             "ru": "T Текст",            "zh_CN": "T 文字"},
    "Insert text field (key T) – adjust size/position with mouse": {"de": "Textfeld einfügen (Taste T) -- Größe/Position mit Maus anpassen", "es": "Insertar campo de texto (tecla T) -- ajustar tamaño/posición con el ratón", "fr": "Insérer un champ texte (touche T) -- ajuster taille/position avec la souris", "ja": "テキストフィールドを挿入（Tキー）-- マウスでサイズ・位置を調整", "pt_BR": "Inserir campo de texto (tecla T) -- ajustar tamanho/posição com o mouse", "ru": "Вставить текстовое поле (клавиша T) -- размер/положение мышью", "zh_CN": "插入文本框（按 T 键）-- 用鼠标调整大小和位置"},
    "🖼 Image":              {"de": "🖼 Bild",            "es": "🖼 Imagen",           "fr": "🖼 Image",            "ja": "🖼 画像",          "pt_BR": "🖼 Imagem",            "ru": "🖼 Изображение",      "zh_CN": "🖼 图片"},
    "Insert image from file (PNG, JPG, SVG …)": {"de": "Bild aus Datei einfügen (PNG, JPG, SVG …)", "es": "Insertar imagen desde archivo (PNG, JPG, SVG …)", "fr": "Insérer une image depuis un fichier (PNG, JPG, SVG …)", "ja": "ファイルから画像を挿入（PNG、JPG、SVG …）", "pt_BR": "Inserir imagem de arquivo (PNG, JPG, SVG …)", "ru": "Вставить изображение из файла (PNG, JPG, SVG …)", "zh_CN": "从文件插入图片（PNG、JPG、SVG …）"},
    "▭ Rectangle":          {"de": "▭ Rechteck",        "es": "▭ Rectángulo",       "fr": "▭ Rectangle",        "ja": "▭ 長方形",        "pt_BR": "▭ Retângulo",         "ru": "▭ Прямоугольник",    "zh_CN": "▭ 矩形"},
    "Insert rectangle (key R) – fill and border color in right panel": {"de": "Rechteck einfügen (Taste R) -- Füll- und Rahmenfarbe im rechten Panel", "es": "Insertar rectángulo (tecla R) -- color de relleno y borde en el panel derecho", "fr": "Insérer un rectangle (touche R) -- couleur de remplissage et de bordure dans le panneau droit", "ja": "長方形を挿入（Rキー）-- 塗りつぶしと枠線の色は右パネルで設定", "pt_BR": "Inserir retângulo (tecla R) -- cor de preenchimento e borda no painel direito", "ru": "Вставить прямоугольник (клавиша R) -- цвет заливки и рамки на правой панели", "zh_CN": "插入矩形（按 R 键）-- 填充色和边框色在右侧面板设置"},
    "◯ Ellipse":             {"de": "◯ Ellipse",         "es": "◯ Elipse",           "fr": "◯ Ellipse",          "ja": "◯ 楕円",          "pt_BR": "◯ Elipse",            "ru": "◯ Эллипс",           "zh_CN": "◯ 椭圆"},
    "Insert ellipse / circle (key E)": {"de": "Ellipse / Kreis einfügen (Taste E)", "es": "Insertar elipse / círculo (tecla E)", "fr": "Insérer une ellipse / un cercle (touche E)", "ja": "楕円・円を挿入（Eキー）", "pt_BR": "Inserir elipse / círculo (tecla E)", "ru": "Вставить эллипс / круг (клавиша E)", "zh_CN": "插入椭圆/圆（按 E 键）"},
    "╱ Line":                {"de": "╱ Linie",           "es": "╱ Línea",            "fr": "╱ Ligne",            "ja": "╱ 直線",          "pt_BR": "╱ Linha",             "ru": "╱ Линия",            "zh_CN": "╱ 直线"},
    "Insert line (key L) – move endpoint with lower resize handle; color via “Border color” in right panel": {"de": "Linie einfügen (Taste L) -- Endpunkt mit unterem Anfasser verschieben; Farbe über \“Rahmenfarbe\“ im rechten Panel", "es": "Insertar línea (tecla L) -- mover extremo con el control inferior; color mediante «Color de borde» en el panel derecho", "fr": "Insérer une ligne (touche L) -- déplacer l'extrémité avec la poignée inférieure ; couleur via « Couleur de bordure » dans le panneau droit", "ja": "直線を挿入（Lキー）-- 下部ハンドルで端点を移動；右パネルの「枠線の色」で色を設定", "pt_BR": "Inserir linha (tecla L) -- mover extremidade com a alça inferior; cor via «Cor da borda» no painel direito", "ru": "Вставить линию (клавиша L) -- конечную точку перемещать нижним маркером; цвет через «Цвет рамки» на правой панели", "zh_CN": "插入直线（按 L 键）-- 用下方手柄移动端点；颜色通过右侧面板中的「边框颜色」设置"},
    "▦ QR Code":             {"de": "▦ QR-Code",         "es": "▦ Código QR",        "fr": "▦ Code QR",          "ja": "▦ QRコード",       "pt_BR": "▦ Código QR",         "ru": "▦ QR-код",           "zh_CN": "▦ 二维码"},
    "Insert QR code – enter URL, text, or vCard data": {"de": "QR-Code einfügen -- URL, Text oder vCard-Daten eingeben", "es": "Insertar código QR -- introducir URL, texto o datos vCard", "fr": "Insérer un code QR -- saisir une URL, du texte ou des données vCard", "ja": "QRコードを挿入 -- URL、テキスト、またはvCardデータを入力", "pt_BR": "Inserir código QR -- inserir URL, texto ou dados vCard", "ru": "Вставить QR-код -- введите URL, текст или данные vCard", "zh_CN": "插入二维码 -- 输入 URL、文本或 vCard 数据"},
    "★ Icon…":               {"de": "★ Symbol …",        "es": "★ Icono…",           "fr": "★ Icône…",           "ja": "★ アイコン…",      "pt_BR": "★ Ícone…",            "ru": "★ Значок…",          "zh_CN": "★ 图标…"},
    "Insert business card icon – scalable and color-adjustable": {"de": "Visitenkarten-Symbol einfügen -- skalierbar und farblich anpassbar", "es": "Insertar icono de tarjeta de visita -- escalable y con color ajustable", "fr": "Insérer une icône de carte de visite -- redimensionnable et couleur réglable", "ja": "名刺アイコンを挿入 -- サイズ・色を自由に変更可能", "pt_BR": "Inserir ícone de cartão de visita -- escalável e com cor ajustável", "ru": "Вставить значок для визитки -- масштабируемый с настраиваемым цветом", "zh_CN": "插入名片图标 -- 可缩放，颜色可调"},
    "↑ Front":               {"de": "↑ Vorne",           "es": "↑ Al frente",        "fr": "↑ Premier plan",     "ja": "↑ 前面へ",        "pt_BR": "↑ À frente",          "ru": "↑ Вперёд",           "zh_CN": "↑ 置于顶层"},
    "Bring selected elements to front (highest layer)": {"de": "Ausgewählte Elemente ganz nach vorne (oberste Ebene)", "es": "Traer los elementos seleccionados al frente (capa más alta)", "fr": "Mettre les éléments sélectionnés au premier plan (couche la plus haute)", "ja": "選択した要素を最前面へ（最上位レイヤー）", "pt_BR": "Trazer elementos selecionados para frente (camada mais alta)", "ru": "Переместить выбранные элементы на передний план (верхний слой)", "zh_CN": "将所选元素置于顶层"},
    "↓ Back":                {"de": "↓ Hinten",          "es": "↓ Al fondo",         "fr": "↓ Arrière-plan",     "ja": "↓ 背面へ",        "pt_BR": "↓ Para trás",         "ru": "↓ Назад",            "zh_CN": "↓ 置于底层"},
    "Send selected elements to back (lowest layer)": {"de": "Ausgewählte Elemente ganz nach hinten (unterste Ebene)", "es": "Enviar los elementos seleccionados al fondo (capa más baja)", "fr": "Mettre les éléments sélectionnés en arrière-plan (couche la plus basse)", "ja": "選択した要素を最背面へ（最下位レイヤー）", "pt_BR": "Enviar elementos selecionados para trás (camada mais baixa)", "ru": "Переместить выбранные элементы на задний план (нижний слой)", "zh_CN": "将所选元素置于底层"},
    "⟳ Undo":                {"de": "⟳ Rückgängig",      "es": "⟳ Deshacer",         "fr": "⟳ Annuler",          "ja": "⟳ 元に戻す",      "pt_BR": "⟳ Desfazer",          "ru": "⟳ Отменить",         "zh_CN": "⟳ 撤销"},
    "Undo last step (Ctrl+Z)":{"de": "Letzten Schritt rückgängig machen (Strg+Z)", "es": "Deshacer último paso (Ctrl+Z)", "fr": "Annuler la dernière action (Ctrl+Z)", "ja": "最後の操作を元に戻す（Ctrl+Z）", "pt_BR": "Desfazer último passo (Ctrl+Z)", "ru": "Отменить последнее действие (Ctrl+Z)", "zh_CN": "撤销上一步（Ctrl+Z）"},
    "⟲ Redo":                {"de": "⟲ Wiederholen",     "es": "⟲ Rehacer",          "fr": "⟲ Rétablir",         "ja": "⟲ やり直し",      "pt_BR": "⟲ Refazer",           "ru": "⟲ Повторить",        "zh_CN": "⟲ 重做"},
    "Redo undone step (Ctrl+Y)":{"de": "Rückgängig gemachten Schritt wiederholen (Strg+Y)", "es": "Rehacer paso deshecho (Ctrl+Y)", "fr": "Rétablir l'action annulée (Ctrl+Y)", "ja": "取り消した操作をやり直す（Ctrl+Y）", "pt_BR": "Refazer passo desfeito (Ctrl+Y)", "ru": "Повторить отменённое действие (Ctrl+Y)", "zh_CN": "重做已撤销的步骤（Ctrl+Y）"},
    "🖨 Preview":             {"de": "🖨 Vorschau",        "es": "🖨 Vista previa",     "fr": "🖨 Aperçu",           "ja": "🖨 プレビュー",    "pt_BR": "🖨 Visualizar",        "ru": "🖨 Предпросмотр",     "zh_CN": "🖨 预览"},
    "Open print preview – shows all cards on the print sheet": {"de": "Druckvorschau öffnen -- alle Karten auf dem Druckbogen anzeigen", "es": "Abrir vista previa de impresión -- muestra todas las tarjetas en la hoja de impresión", "fr": "Ouvrir l'aperçu avant impression -- affiche toutes les cartes sur la feuille", "ja": "印刷プレビューを開く -- 印刷用紙上のすべてのカードを表示", "pt_BR": "Abrir visualização de impressão -- exibe todos os cartões na folha de impressão", "ru": "Открыть предпросмотр печати -- показывает все карточки на листе", "zh_CN": "打开打印预览 -- 显示打印纸张上的所有名片"},

    # ── MainWindow -- align toolbar ─────────────────────────────────────────
    "Align":                    {"de": "Ausrichten",            "es": "Alinear",                    "fr": "Aligner",                    "ja": "整列",           "pt_BR": "Alinhar",                 "ru": "Выравнивание",               "zh_CN": "对齐"},
    "To Card:":                 {"de": "Zur Karte:",            "es": "A la tarjeta:",              "fr": "Vers la carte :",            "ja": "カード基準：",   "pt_BR": "À tarjeta:",              "ru": "По карточке:",               "zh_CN": "相对名片："},
    "Align left to card":       {"de": "Links an Karte ausrichten","es": "Alinear a la izquierda de la tarjeta","fr": "Aligner à gauche de la carte","ja": "カードの左に揃える","pt_BR": "Alinhar à esquerda da tarjeta","ru": "Выровнять по левому краю карточки","zh_CN": "与名片左对齐"},
    "Center horizontally on card": {"de": "Horizontal auf Karte zentrieren","es": "Centrar horizontalmente en la tarjeta","fr": "Centrer horizontalement sur la carte","ja": "カード上で水平方向に中央揃え","pt_BR": "Centralizar horizontalmente na tarjeta","ru": "Центрировать горизонтально на карточке","zh_CN": "在名片上水平居中"},
    "Align right to card":      {"de": "Rechts an Karte ausrichten","es": "Alinear a la derecha de la tarjeta","fr": "Aligner à droite de la carte","ja": "カードの右に揃える","pt_BR": "Alinhar à direita da tarjeta","ru": "Выровнять по правому краю карточки","zh_CN": "与名片右对齐"},
    "Align top to card":        {"de": "Oben an Karte ausrichten","es": "Alinear arriba de la tarjeta","fr": "Aligner en haut de la carte","ja": "カードの上に揃える","pt_BR": "Alinhar no topo da tarjeta","ru": "Выровнять по верхнему краю карточки","zh_CN": "与名片顶部对齐"},
    "Center vertically on card":{"de": "Vertikal auf Karte zentrieren","es": "Centrar verticalmente en la tarjeta","fr": "Centrer verticalement sur la carte","ja": "カード上で垂直方向に中央揃え","pt_BR": "Centralizar verticalmente na tarjeta","ru": "Центрировать вертикально на карточке","zh_CN": "在名片上垂直居中"},
    "Align bottom to card":     {"de": "Unten an Karte ausrichten","es": "Alinear abajo de la tarjeta","fr": "Aligner en bas de la carte","ja": "カードの下に揃える","pt_BR": "Alinhar na parte inferior da tarjeta","ru": "Выровнять по нижнему краю карточки","zh_CN": "与名片底部对齐"},
    "To Selection:":            {"de": "Zur Auswahl:",          "es": "A la selección:",            "fr": "Vers la sélection :",        "ja": "選択基準：",     "pt_BR": "À seleção:",              "ru": "По выделению:",              "zh_CN": "相对所选："},
    "Align left edges":         {"de": "Linkskanten ausrichten","es": "Alinear bordes izquierdos",  "fr": "Aligner les bords gauches",  "ja": "左端を揃える",   "pt_BR": "Alinhar bordas esquerdas", "ru": "Выровнять по левому краю",   "zh_CN": "左边缘对齐"},
    "Center on common horizontal axis": {"de": "Auf gemeinsamer horizontaler Achse zentrieren","es": "Centrar en eje horizontal común","fr": "Centrer sur l'axe horizontal commun","ja": "共通の水平軸上で中央揃え","pt_BR": "Centralizar no eixo horizontal comum","ru": "По общей горизонтальной оси","zh_CN": "在公共水平轴居中"},
    "Align right edges":        {"de": "Rechtskanten ausrichten","es": "Alinear bordes derechos",   "fr": "Aligner les bords droits",   "ja": "右端を揃える",   "pt_BR": "Alinhar bordas direitas",  "ru": "Выровнять по правому краю",  "zh_CN": "右边缘对齐"},
    "Align top edges":          {"de": "Oberkanten ausrichten", "es": "Alinear bordes superiores",  "fr": "Aligner les bords supérieurs","ja": "上端を揃える",   "pt_BR": "Alinhar bordas superiores","ru": "Выровнять по верхнему краю", "zh_CN": "顶边缘对齐"},
    "Center on common vertical axis": {"de": "Auf gemeinsamer vertikaler Achse zentrieren","es": "Centrar en eje vertical común","fr": "Centrer sur l'axe vertical commun","ja": "共通の垂直軸上で中央揃え","pt_BR": "Centralizar no eixo vertical comum","ru": "По общей вертикальной оси","zh_CN": "在公共垂直轴居中"},
    "Align bottom edges":       {"de": "Unterkanten ausrichten","es": "Alinear bordes inferiores",  "fr": "Aligner les bords inférieurs","ja": "下端を揃える",   "pt_BR": "Alinhar bordas inferiores","ru": "Выровнять по нижнему краю",  "zh_CN": "底边缘对齐"},
    "Distribute:":              {"de": "Verteilen:",            "es": "Distribuir:",                "fr": "Distribuer :",               "ja": "分布：",         "pt_BR": "Distribuir:",             "ru": "Распределить:",              "zh_CN": "分布："},
    "Distribute horizontally (≥3 elements)": {"de": "Horizontal verteilen (≥ 3 Elemente)", "es": "Distribuir horizontalmente (≥ 3 elementos)", "fr": "Distribuer horizontalement (≥ 3 éléments)", "ja": "水平方向に分布（3つ以上の要素）", "pt_BR": "Distribuir horizontalmente (≥ 3 elementos)", "ru": "Распределить горизонтально (≥ 3 элементов)", "zh_CN": "水平分布（≥3 个元素）"},
    "Distribute vertically (≥3 elements)":   {"de": "Vertikal verteilen (≥ 3 Elemente)",   "es": "Distribuir verticalmente (≥ 3 elementos)",   "fr": "Distribuer verticalement (≥ 3 éléments)",   "ja": "垂直方向に分布（3つ以上の要素）", "pt_BR": "Distribuir verticalmente (≥ 3 elementos)",   "ru": "Распределить вертикально (≥ 3 элементов)",   "zh_CN": "垂直分布（≥3 个元素）"},
    "Content:":                 {"de": "Inhalt:",               "es": "Contenido:",                 "fr": "Contenu :",                  "ja": "コンテンツ：",   "pt_BR": "Conteúdo:",               "ru": "Содержимое:",                "zh_CN": "内容："},
    "⊡ Fit":                    {"de": "⊡ Anpassen",            "es": "⊡ Ajustar",                  "fr": "⊡ Adapter",                  "ja": "⊡ 合わせる",     "pt_BR": "⊡ Ajustar",               "ru": "⊡ По размеру",               "zh_CN": "⊡ 适应"},
    "Fit to content (text→text size, image→aspect ratio, QR→square)": {"de": "An Inhalt anpassen (Text→Textgröße, Bild→Seitenverhältnis, QR→Quadrat)", "es": "Ajustar al contenido (texto→tamaño de texto, imagen→proporción, QR→cuadrado)", "fr": "Adapter au contenu (texte→taille du texte, image→format, QR→carré)", "ja": "コンテンツに合わせる（テキスト→テキストサイズ、画像→アスペクト比、QR→正方形）", "pt_BR": "Ajustar ao conteúdo (texto→tamanho do texto, imagem→proporção, QR→quadrado)", "ru": "По размеру содержимого (текст→размер текста, изображение→пропорции, QR→квадрат)", "zh_CN": "适应内容（文字→文字大小，图片→宽高比，QR→正方形）"},

    # ── MainWindow -- status / callbacks ───────────────────────────────────
    "Card: {name} | {side}":                {"de": "Karte: {name} | {side}",            "es": "Tarjeta: {name} | {side}",           "fr": "Carte : {name} | {side}",            "ja": "カード: {name} | {side}",    "pt_BR": "Cartão: {name} | {side}",         "ru": "Карточка: {name} | {side}",          "zh_CN": "名片：{name} | {side}"},
    "Side: {side}":                         {"de": "Seite: {side}",                     "es": "Cara: {side}",                       "fr": "Côté : {side}",                      "ja": "面: {side}",                 "pt_BR": "Lado: {side}",                    "ru": "Сторона: {side}",                    "zh_CN": "面：{side}"},
    "New Card":                             {"de": "Neue Karte",                        "es": "Nueva tarjeta",                      "fr": "Nouvelle carte",                     "ja": "新規カード",                 "pt_BR": "Novo cartão",                     "ru": "Новая карточка",                     "zh_CN": "新建名片"},
    "Name:":                                {"de": "Name:",                             "es": "Nombre:",                            "fr": "Nom :",                              "ja": "名前：",                     "pt_BR": "Nome:",                           "ru": "Название:",                          "zh_CN": "名称："},
    "Add card":                             {"de": "Karte hinzufügen",                  "es": "Añadir tarjeta",                     "fr": "Ajouter la carte",                   "ja": "カードを追加",               "pt_BR": "Adicionar cartão",                "ru": "Добавить карточку",                  "zh_CN": "添加名片"},
    "Duplicate card":                       {"de": "Karte duplizieren",                 "es": "Duplicar tarjeta",                   "fr": "Dupliquer la carte",                 "ja": "カードを複製",               "pt_BR": "Duplicar cartão",                 "ru": "Дублировать карточку",               "zh_CN": "复制名片"},
    " (Copy)":                              {"de": " (Kopie)",                          "es": " (copia)",                           "fr": " (copie)",                           "ja": " (コピー)",                  "pt_BR": " (cópia)",                        "ru": " (копия)",                           "zh_CN": "（副本）"},
    "At least one card must remain.":       {"de": "Es muss mindestens eine Karte vorhanden sein.", "es": "Debe quedar al menos una tarjeta.", "fr": "Il doit rester au moins une carte.", "ja": "カードは少なくとも1枚必要です。", "pt_BR": "Deve restar pelo menos um cartão.", "ru": "Должна остаться хотя бы одна карточка.", "zh_CN": "至少需要保留一张名片。"},
    "Rename":                               {"de": "Umbenennen",                        "es": "Renombrar",                          "fr": "Renommer",                           "ja": "名前の変更",                 "pt_BR": "Renomear",                        "ru": "Переименовать",                      "zh_CN": "重命名"},
    "New name:":                            {"de": "Neuer Name:",                       "es": "Nuevo nombre:",                      "fr": "Nouveau nom :",                      "ja": "新しい名前：",               "pt_BR": "Novo nome:",                      "ru": "Новое название:",                    "zh_CN": "新名称："},
    "Insert text":                          {"de": "Text einfügen",                     "es": "Insertar texto",                     "fr": "Insérer un texte",                   "ja": "テキストを挿入",             "pt_BR": "Inserir texto",                   "ru": "Вставить текст",                     "zh_CN": "插入文字"},
    "Select Image":                         {"de": "Bild auswählen",                    "es": "Seleccionar imagen",                 "fr": "Sélectionner une image",             "ja": "画像を選択",                 "pt_BR": "Selecionar imagem",               "ru": "Выбрать изображение",                "zh_CN": "选择图片"},
    "Images (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp)": {"de": "Bilder (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp)", "es": "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp)", "fr": "Images (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp)", "ja": "画像ファイル (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp)", "pt_BR": "Imagens (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp)", "ru": "Изображения (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp)", "zh_CN": "图片 (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp)"},
    "Insert image":                         {"de": "Bild einfügen",                     "es": "Insertar imagen",                    "fr": "Insérer une image",                  "ja": "画像を挿入",                 "pt_BR": "Inserir imagem",                  "ru": "Вставить изображение",               "zh_CN": "插入图片"},
    "Insert rectangle":                     {"de": "Rechteck einfügen",                 "es": "Insertar rectángulo",                "fr": "Insérer un rectangle",               "ja": "長方形を挿入",               "pt_BR": "Inserir retângulo",               "ru": "Вставить прямоугольник",             "zh_CN": "插入矩形"},
    "Insert ellipse":                       {"de": "Ellipse einfügen",                  "es": "Insertar elipse",                    "fr": "Insérer une ellipse",                "ja": "楕円を挿入",                 "pt_BR": "Inserir elipse",                  "ru": "Вставить эллипс",                    "zh_CN": "插入椭圆"},
    "Insert line":                          {"de": "Linie einfügen",                    "es": "Insertar línea",                     "fr": "Insérer une ligne",                  "ja": "直線を挿入",                 "pt_BR": "Inserir linha",                   "ru": "Вставить линию",                     "zh_CN": "插入直线"},
    "Content (URL, text, vCard …):":        {"de": "Inhalt (URL, Text, vCard …):",      "es": "Contenido (URL, texto, vCard …):",   "fr": "Contenu (URL, texte, vCard …) :",   "ja": "コンテンツ（URL、テキスト、vCard…）：","pt_BR": "Conteúdo (URL, texto, vCard …):", "ru": "Содержимое (URL, текст, vCard …):", "zh_CN": "内容（URL、文字、vCard …）："},
    "Insert QR code":                       {"de": "QR-Code einfügen",                  "es": "Insertar código QR",                 "fr": "Insérer un code QR",                 "ja": "QRコードを挿入",             "pt_BR": "Inserir código QR",               "ru": "Вставить QR-код",                    "zh_CN": "插入二维码"},
    "Insert icon":                          {"de": "Symbol einfügen",                   "es": "Insertar icono",                     "fr": "Insérer une icône",                  "ja": "アイコンを挿入",             "pt_BR": "Inserir ícone",                   "ru": "Вставить значок",                    "zh_CN": "插入图标"},
    "Properties changed":                   {"de": "Eigenschaften geändert",            "es": "Propiedades modificadas",            "fr": "Propriétés modifiées",               "ja": "プロパティを変更",           "pt_BR": "Propriedades alteradas",          "ru": "Свойства изменены",                  "zh_CN": "属性已更改"},
    "Selected: {etype} | {count} element(s)":{"de": "Ausgewählt: {etype} | {count} Element(e)", "es": "Seleccionado: {etype} | {count} elemento(s)", "fr": "Sélectionné : {etype} | {count} élément(s)", "ja": "選択中: {etype} | {count} 個の要素", "pt_BR": "Selecionado: {etype} | {count} elemento(s)", "ru": "Выбрано: {etype} | {count} элемент(ов)", "zh_CN": "已选：{etype} | {count} 个元素"},
    "Move/Resize":                          {"de": "Verschieben/Skalieren",             "es": "Mover/Redimensionar",                "fr": "Déplacer/Redimensionner",            "ja": "移動/サイズ変更",            "pt_BR": "Mover/Redimensionar",             "ru": "Перемещение/Масштабирование",        "zh_CN": "移动/调整大小"},
    "Language Changed":                     {"de": "Sprache geändert",                  "es": "Idioma cambiado",                    "fr": "Langue modifiée",                    "ja": "言語が変更されました",       "pt_BR": "Idioma alterado",                 "ru": "Язык изменён",                       "zh_CN": "语言已更改"},
    "The language will change after restarting the application.": {"de": "Die Sprache wird nach dem Neustart der Anwendung geändert.", "es": "El idioma cambiará después de reiniciar la aplicación.", "fr": "La langue changera après le redémarrage de l'application.", "ja": "アプリケーションを再起動すると、言語が変更されます。", "pt_BR": "O idioma será alterado após reiniciar o aplicativo.", "ru": "Язык изменится после перезапуска приложения.", "zh_CN": "重启应用程序后，语言将会更改。"},

    # ── MainWindow -- paper library ─────────────────────────────────────────
    "Save Template":            {"de": "Vorlage speichern",         "es": "Guardar plantilla",          "fr": "Enregistrer le modèle",      "ja": "テンプレートを保存",     "pt_BR": "Salvar modelo",               "ru": "Сохранить шаблон",           "zh_CN": "保存模板"},
    "Template name:":           {"de": "Name der Vorlage:",         "es": "Nombre de la plantilla:",    "fr": "Nom du modèle :",            "ja": "テンプレート名：",       "pt_BR": "Nome do modelo:",             "ru": "Название шаблона:",          "zh_CN": "模板名称："},
    "Saved":                    {"de": "Gespeichert",               "es": "Guardado",                   "fr": "Enregistré",                 "ja": "保存しました",           "pt_BR": "Salvo",                       "ru": "Сохранено",                  "zh_CN": "已保存"},
    "“{name}” has been saved to the library.": {"de": "\"{name}\" wurde in der Bibliothek gespeichert.", "es": "«{name}» se ha guardado en la biblioteca.", "fr": "« {name} » a été enregistré dans la bibliothèque.", "ja": "「{name}」をライブラリに保存しました。", "pt_BR": "«{name}» foi salvo na biblioteca.", "ru": "«{name}» сохранён в библиотеке.", "zh_CN": "「{name}」已保存到库中。"},
    "{name}  ({pw:.0f}×{ph:.0f} mm,  {cols}×{rows} cards)": {"de": "{name}  ({pw:.0f}×{ph:.0f} mm,  {cols}×{rows} Karten)", "es": "{name}  ({pw:.0f}×{ph:.0f} mm,  {cols}×{rows} tarjetas)", "fr": "{name}  ({pw:.0f}×{ph:.0f} mm,  {cols}×{rows} cartes)", "ja": "{name}  ({pw:.0f}×{ph:.0f} mm,  {cols}×{rows} 枚)", "pt_BR": "{name}  ({pw:.0f}×{ph:.0f} mm,  {cols}×{rows} cartões)", "ru": "{name}  ({pw:.0f}×{ph:.0f} мм,  {cols}×{rows} карт)", "zh_CN": "{name}  ({pw:.0f}×{ph:.0f} mm，{cols}×{rows} 张名片)"},
    "Paper Template Library":   {"de": "Vorlagenbibliothek",        "es": "Biblioteca de plantillas",   "fr": "Bibliothèque de modèles",    "ja": "テンプレートライブラリ", "pt_BR": "Biblioteca de modelos",       "ru": "Библиотека шаблонов",        "zh_CN": "模板库"},
    "★ = own template  –  double-click to load": {"de": "★ = eigene Vorlage  --  Doppelklick zum Laden", "es": "★ = plantilla propia  --  doble clic para cargar", "fr": "★ = modèle personnel  --  double-clic pour charger", "ja": "★ = 自分のテンプレート  --  ダブルクリックで読み込む", "pt_BR": "★ = modelo próprio  --  clique duplo para carregar", "ru": "★ = собственный шаблон  --  двойной щелчок для загрузки", "zh_CN": "★ = 自定义模板  --  双击加载"},
    "Load":                     {"de": "Laden",                     "es": "Cargar",                     "fr": "Charger",                    "ja": "読み込む",               "pt_BR": "Carregar",                    "ru": "Загрузить",                  "zh_CN": "加载"},
    "Delete":                   {"de": "Löschen",                   "es": "Eliminar",                   "fr": "Supprimer",                  "ja": "削除",                   "pt_BR": "Excluir",                     "ru": "Удалить",                    "zh_CN": "删除"},
    "Close":                    {"de": "Schließen",                 "es": "Cerrar",                     "fr": "Fermer",                     "ja": "閉じる",                 "pt_BR": "Fechar",                      "ru": "Закрыть",                    "zh_CN": "关闭"},
    "Delete Template":          {"de": "Vorlage löschen",           "es": "Eliminar plantilla",         "fr": "Supprimer le modèle",        "ja": "テンプレートを削除",     "pt_BR": "Excluir modelo",              "ru": "Удалить шаблон",             "zh_CN": "删除模板"},
    "“{name}” will be permanently deleted from the library. Continue?":  {"de": "“{name}” wird unwiderruflich aus der Bibliothek gelöscht. Fortfahren?", "es": "«{name}» se eliminará permanentemente de la biblioteca. ¿Continuar?", "fr": "« {name} » sera définitivement supprimé de la bibliothèque. Continuer ?", "ja": "「{name}」はライブラリから完全に削除されます。続けますか？", "pt_BR": "«{name}» será excluído permanentemente da biblioteca. Continuar?", "ru": "«{name}» будет безвозвратно удалён из библиотеки. Продолжить?", "zh_CN": "「{name}」将从库中永久删除。是否继续？"},
    "Card 1":                   {"de": "Karte 1",                   "es": "Tarjeta 1",                  "fr": "Carte 1",                    "ja": "カード 1",               "pt_BR": "Cartão 1",                    "ru": "Карточка 1",                 "zh_CN": "名片 1"},
    "(none)":                   {"de": "(keine)",                   "es": "(ninguno)",                  "fr": "(aucun)",                    "ja": "（なし）",               "pt_BR": "(nenhum)",                    "ru": "(нет)",                      "zh_CN": "（无）"},
    "Clear List":               {"de": "Liste leeren",              "es": "Borrar lista",               "fr": "Effacer la liste",           "ja": "リストをクリア",         "pt_BR": "Limpar lista",                "ru": "Очистить список",            "zh_CN": "清空列表"},
    "File Not Found":           {"de": "Datei nicht gefunden",      "es": "Archivo no encontrado",      "fr": "Fichier introuvable",        "ja": "ファイルが見つかりません","pt_BR": "Arquivo não encontrado",      "ru": "Файл не найден",             "zh_CN": "文件未找到"},
    "The file was not found:\n{path}": {"de": "Die Datei wurde nicht gefunden:\n{path}", "es": "El archivo no se encontró:\n{path}", "fr": "Le fichier est introuvable :\n{path}", "ja": "ファイルが見つかりませんでした：\n{path}", "pt_BR": "O arquivo não foi encontrado:\n{path}", "ru": "Файл не найден:\n{path}", "zh_CN": "未找到文件：\n{path}"},
    "Error Loading":            {"de": "Fehler beim Laden",         "es": "Error al cargar",            "fr": "Erreur de chargement",       "ja": "読み込みエラー",         "pt_BR": "Erro ao carregar",            "ru": "Ошибка загрузки",            "zh_CN": "加载错误"},
    "Open Project":             {"de": "Projekt öffnen",            "es": "Abrir proyecto",             "fr": "Ouvrir un projet",           "ja": "プロジェクトを開く",     "pt_BR": "Abrir projeto",               "ru": "Открыть проект",             "zh_CN": "打开项目"},
    "Business Card Project (*.vcproj)": {"de": "Visitenkarten-Projekt (*.vcproj)", "es": "Proyecto de tarjeta de visita (*.vcproj)", "fr": "Projet de carte de visite (*.vcproj)", "ja": "名刺プロジェクト (*.vcproj)", "pt_BR": "Projeto de cartão de visita (*.vcproj)", "ru": "Проект визитки (*.vcproj)", "zh_CN": "名片项目 (*.vcproj)"},
    "Save As":                  {"de": "Speichern unter",           "es": "Guardar como",               "fr": "Enregistrer sous",           "ja": "別名で保存",             "pt_BR": "Salvar como",                 "ru": "Сохранить как",              "zh_CN": "另存为"},
    "CardForge Project (*.vcproj)": {"de": "CardForge-Projekt (*.vcproj)", "es": "Proyecto CardForge (*.vcproj)", "fr": "Projet CardForge (*.vcproj)", "ja": "CardForge プロジェクト (*.vcproj)", "pt_BR": "Projeto CardForge (*.vcproj)", "ru": "Проект CardForge (*.vcproj)", "zh_CN": "CardForge 项目 (*.vcproj)"},
    "Saved: {path}":            {"de": "Gespeichert: {path}",       "es": "Guardado: {path}",           "fr": "Enregistré : {path}",        "ja": "保存しました: {path}",   "pt_BR": "Salvo: {path}",               "ru": "Сохранено: {path}",          "zh_CN": "已保存：{path}"},
    "Error Saving":             {"de": "Fehler beim Speichern",     "es": "Error al guardar",           "fr": "Erreur d'enregistrement",    "ja": "保存エラー",             "pt_BR": "Erro ao salvar",              "ru": "Ошибка сохранения",          "zh_CN": "保存错误"},
    "Export as Template":       {"de": "Als Vorlage exportieren",   "es": "Exportar como plantilla",    "fr": "Exporter comme modèle",      "ja": "テンプレートとしてエクスポート","pt_BR": "Exportar como modelo",   "ru": "Экспорт как шаблон",         "zh_CN": "导出为模板"},
    "CardForge Template (*.vctemplate)": {"de": "CardForge-Vorlage (*.vctemplate)", "es": "Plantilla CardForge (*.vctemplate)", "fr": "Modèle CardForge (*.vctemplate)", "ja": "CardForge テンプレート (*.vctemplate)", "pt_BR": "Modelo CardForge (*.vctemplate)", "ru": "Шаблон CardForge (*.vctemplate)", "zh_CN": "CardForge 模板 (*.vctemplate)"},
    "Template exported: {path}":{"de": "Vorlage exportiert: {path}","es": "Plantilla exportada: {path}","fr": "Modèle exporté : {path}",    "ja": "テンプレートをエクスポートしました: {path}", "pt_BR": "Modelo exportado: {path}", "ru": "Шаблон экспортирован: {path}", "zh_CN": "模板已导出：{path}"},
    "Import Template":          {"de": "Vorlage importieren",       "es": "Importar plantilla",         "fr": "Importer un modèle",         "ja": "テンプレートをインポート","pt_BR": "Importar modelo",             "ru": "Импортировать шаблон",       "zh_CN": "导入模板"},
    " (imported)":              {"de": " (importiert)",             "es": " (importado)",               "fr": " (importé)",                 "ja": "（インポート済み）",     "pt_BR": " (importado)",                "ru": " (импортирован)",            "zh_CN": "（已导入）"},
    "Select Font File":         {"de": "Schriftdatei auswählen",    "es": "Seleccionar archivo de fuente","fr": "Sélectionner un fichier de police","ja": "フォントファイルを選択","pt_BR": "Selecionar arquivo de fonte","ru": "Выбрать файл шрифта",        "zh_CN": "选择字体文件"},
    "Font Files (*.ttf *.otf)": {"de": "Schriftdateien (*.ttf *.otf)","es": "Archivos de fuente (*.ttf *.otf)","fr": "Fichiers de police (*.ttf *.otf)","ja": "フォントファイル (*.ttf *.otf)","pt_BR": "Arquivos de fonte (*.ttf *.otf)","ru": "Файлы шрифтов (*.ttf *.otf)","zh_CN": "字体文件 (*.ttf *.otf)"},
    "Font could not be loaded.":{"de": "Die Schrift konnte nicht geladen werden.", "es": "No se pudo cargar la fuente.", "fr": "Impossible de charger la police.", "ja": "フォントを読み込めませんでした。", "pt_BR": "Não foi possível carregar a fonte.", "ru": "Не удалось загрузить шрифт.", "zh_CN": "无法加载字体。"},
    "Font Loaded":              {"de": "Schrift geladen",           "es": "Fuente cargada",             "fr": "Police chargée",             "ja": "フォントを読み込みました","pt_BR": "Fonte carregada",             "ru": "Шрифт загружен",             "zh_CN": "字体已加载"},
    "Font(s) added:\n{families}":{"de": "Schrift(en) hinzugefügt:\n{families}", "es": "Fuente(s) añadida(s):\n{families}", "fr": "Police(s) ajoutée(s) :\n{families}", "ja": "フォントを追加しました：\n{families}", "pt_BR": "Fonte(s) adicionada(s):\n{families}", "ru": "Шрифт(ы) добавлен(ы):\n{families}", "zh_CN": "已添加字体：\n{families}"},
    "{count} card(s) created from mail merge.": {"de": "{count} Karte(n) per Serienbrief erstellt.", "es": "{count} tarjeta(s) creada(s) mediante combinación de correspondencia.", "fr": "{count} carte(s) créée(s) par publipostage.", "ja": "差し込み印刷で {count} 枚のカードを作成しました。", "pt_BR": "{count} cartão(ões) criado(s) por mala direta.", "ru": "Создано {count} карточек(ки) серийным письмом.", "zh_CN": "通过邮件合并创建了 {count} 张名片。"},
    "Done":                     {"de": "Fertig",                    "es": "Hecho",                      "fr": "Terminé",                    "ja": "完了",                   "pt_BR": "Concluído",                   "ru": "Готово",                     "zh_CN": "完成"},
    "Discard Changes?":         {"de": "Änderungen verwerfen?",     "es": "¿Descartar cambios?",        "fr": "Abandonner les modifications ?","ja": "変更を破棄しますか？",  "pt_BR": "Descartar alterações?",       "ru": "Отклонить изменения?",       "zh_CN": "放弃更改？"},
    "There are unsaved changes. Continue?": {"de": "Es gibt ungespeicherte Änderungen. Fortfahren?", "es": "Hay cambios sin guardar. ¿Continuar?", "fr": "Il y a des modifications non enregistrées. Continuer ?", "ja": "保存されていない変更があります。続けますか？", "pt_BR": "Há alterações não salvas. Continuar?", "ru": "Есть несохранённые изменения. Продолжить?", "zh_CN": "有未保存的更改。是否继续？"},

    # ── PaperTemplateDialog ────────────────────────────────────────────────
    "Edit Paper Template":      {"de": "Druckvorlage bearbeiten",   "es": "Editar plantilla de papel",  "fr": "Modifier le format d'impression","ja": "用紙テンプレートを編集","pt_BR": "Editar modelo de papel",      "ru": "Изменить шаблон листа",      "zh_CN": "编辑纸张模板"},
    "PAPER TEMPLATE":           {"de": "DRUCKVORLAGE",              "es": "PLANTILLA DE PAPEL",         "fr": "FORMAT D'IMPRESSION",        "ja": "用紙テンプレート",       "pt_BR": "MODELO DE PAPEL",             "ru": "ШАБЛОН ЛИСТА",               "zh_CN": "纸张模板"},
    "Template name …":          {"de": "Vorlagenname …",            "es": "Nombre de la plantilla…",    "fr": "Nom du modèle…",             "ja": "テンプレート名…",        "pt_BR": "Nome do modelo…",             "ru": "Название шаблона…",          "zh_CN": "模板名称…"},
    "Paper Format":             {"de": "Papierformat",              "es": "Formato de papel",           "fr": "Format de papier",           "ja": "用紙サイズ",             "pt_BR": "Formato de papel",            "ru": "Формат бумаги",              "zh_CN": "纸张格式"},
    "Preset:":                  {"de": "Voreinstellung:",           "es": "Predefinido:",               "fr": "Prédéfini :",                "ja": "プリセット：",           "pt_BR": "Predefinição:",               "ru": "Шаблон:",                    "zh_CN": "预设："},
    "Width:":                   {"de": "Breite:",                   "es": "Anchura:",                   "fr": "Largeur :",                  "ja": "幅：",                   "pt_BR": "Largura:",                    "ru": "Ширина:",                    "zh_CN": "宽度："},
    "Height:":                  {"de": "Höhe:",                     "es": "Altura:",                    "fr": "Hauteur :",                  "ja": "高さ：",                 "pt_BR": "Altura:",                     "ru": "Высота:",                    "zh_CN": "高度："},
    "Business Card":            {"de": "Visitenkarte",              "es": "Tarjeta de visita",          "fr": "Carte de visite",            "ja": "名刺",                   "pt_BR": "Cartão de visita",            "ru": "Визитная карточка",          "zh_CN": "名片"},
    "Page Margins":             {"de": "Seitenränder",              "es": "Márgenes de página",         "fr": "Marges de page",             "ja": "ページ余白",             "pt_BR": "Margens da página",           "ru": "Поля страницы",              "zh_CN": "页边距"},
    "Top:":                     {"de": "Oben:",                     "es": "Superior:",                  "fr": "Haut :",                     "ja": "上：",                   "pt_BR": "Superior:",                   "ru": "Верхнее:",                   "zh_CN": "上："},
    "Bottom:":                  {"de": "Unten:",                    "es": "Inferior:",                  "fr": "Bas :",                      "ja": "下：",                   "pt_BR": "Inferior:",                   "ru": "Нижнее:",                    "zh_CN": "下："},
    "Left:":                    {"de": "Links:",                    "es": "Izquierdo:",                 "fr": "Gauche :",                   "ja": "左：",                   "pt_BR": "Esquerdo:",                   "ru": "Левое:",                     "zh_CN": "左："},
    "Right:":                   {"de": "Rechts:",                   "es": "Derecho:",                   "fr": "Droite :",                   "ja": "右：",                   "pt_BR": "Direito:",                    "ru": "Правое:",                    "zh_CN": "右："},
    "Gaps & Count":             {"de": "Abstände & Anzahl",         "es": "Espaciado y cantidad",       "fr": "Espacement et nombre",       "ja": "間隔と枚数",             "pt_BR": "Espaçamento e quantidade",    "ru": "Отступы и количество",       "zh_CN": "间距与数量"},
    "Horizontal:":              {"de": "Horizontal:",               "es": "Horizontal:",                "fr": "Horizontal :",               "ja": "水平：",                 "pt_BR": "Horizontal:",                 "ru": "Горизонтально:",             "zh_CN": "水平："},
    "Vertical:":                {"de": "Vertikal:",                 "es": "Vertical:",                  "fr": "Vertical :",                 "ja": "垂直：",                 "pt_BR": "Vertical:",                   "ru": "Вертикально:",               "zh_CN": "垂直："},
    "Columns:":                 {"de": "Spalten:",                  "es": "Columnas:",                  "fr": "Colonnes :",                 "ja": "列：",                   "pt_BR": "Colunas:",                    "ru": "Столбцы:",                   "zh_CN": "列数："},
    "Rows:":                    {"de": "Zeilen:",                   "es": "Filas:",                     "fr": "Lignes :",                   "ja": "行：",                   "pt_BR": "Linhas:",                     "ru": "Строки:",                    "zh_CN": "行数："},
    "↺  Auto-calculate":        {"de": "↺  Automatisch berechnen", "es": "↺  Calcular automáticamente","fr": "↺  Calculer automatiquement","ja": "↺  自動計算",             "pt_BR": "↺  Calcular automaticamente", "ru": "↺  Авторасчёт",              "zh_CN": "↺  自动计算"},
    "Template":                 {"de": "Vorlage",                   "es": "Plantilla",                  "fr": "Modèle",                     "ja": "テンプレート",           "pt_BR": "Modelo",                      "ru": "Шаблон",                     "zh_CN": "模板"},

    # ── PrintExportDialog ──────────────────────────────────────────────────
    "Print / PDF Export":       {"de": "Drucken / PDF-Export",      "es": "Imprimir / Exportar PDF",    "fr": "Imprimer / Exporter PDF",    "ja": "印刷 / PDF出力",         "pt_BR": "Imprimir / Exportar PDF",     "ru": "Печать / Экспорт PDF",       "zh_CN": "打印 / 导出 PDF"},
    "Cards":                    {"de": "Karten",                    "es": "Tarjetas",                   "fr": "Cartes",                     "ja": "カード",                 "pt_BR": "Cartões",                     "ru": "Карточки",                   "zh_CN": "名片"},
    "All cards":                {"de": "Alle Karten",               "es": "Todas las tarjetas",         "fr": "Toutes les cartes",          "ja": "すべてのカード",         "pt_BR": "Todos os cartões",            "ru": "Все карточки",               "zh_CN": "所有名片"},
    "Selected cards:":          {"de": "Ausgewählte Karten:",       "es": "Tarjetas seleccionadas:",    "fr": "Cartes sélectionnées :",     "ja": "選択したカード：",       "pt_BR": "Cartões selecionados:",       "ru": "Выбранные карточки:",         "zh_CN": "所选名片："},
    "Sides":                    {"de": "Seiten",                    "es": "Caras",                      "fr": "Faces",                      "ja": "面",                     "pt_BR": "Lados",                       "ru": "Стороны",                    "zh_CN": "面"},
    "Duplex (front & back)":    {"de": "Duplex (Vorder- & Rückseite)", "es": "Dúplex (anverso y reverso)", "fr": "Recto-verso (recto et verso)", "ja": "両面（表面・裏面）",    "pt_BR": "Duplex (frente e verso)",     "ru": "Двусторонняя (обе стороны)", "zh_CN": "双面（正面和背面）"},
    "Single-sided – front":     {"de": "Einseitig -- Vorderseite",  "es": "Una cara -- anverso",         "fr": "Recto seul",                 "ja": "片面 -- 表面のみ",        "pt_BR": "Frente apenas",               "ru": "Односторонняя -- лицевая",    "zh_CN": "单面 -- 正面"},
    "Single-sided – back":      {"de": "Einseitig -- Rückseite",    "es": "Una cara -- reverso",         "fr": "Verso seul",                 "ja": "片面 -- 裏面のみ",        "pt_BR": "Verso apenas",                "ru": "Односторонняя -- обратная",   "zh_CN": "单面 -- 背面"},
    "  Binding edge:":          {"de": "  Binderand:",              "es": "  Borde de encuadernación:", "fr": "  Bord de reliure :",        "ja": "  とじ方向：",            "pt_BR": "  Margem de encadernação:",   "ru": "  Корешковое поле:",          "zh_CN": "  装订边："},
    "Long edge (portrait, default)": {"de": "Lange Seite (Hochformat, Standard)", "es": "Borde largo (vertical, predeterminado)", "fr": "Grand côté (portrait, par défaut)", "ja": "長辺とじ（縦向き、デフォルト）", "pt_BR": "Borda longa (retrato, padrão)", "ru": "Длинная сторона (книжная, по умолчанию)", "zh_CN": "长边（纵向，默认）"},
    "Short edge (landscape)":   {"de": "Kurze Seite (Querformat)", "es": "Borde corto (horizontal)",  "fr": "Petit côté (paysage)",       "ja": "短辺とじ（横向き）",     "pt_BR": "Borda curta (paisagem)",      "ru": "Короткая сторона (альбомная)","zh_CN": "短边（横向）"},
    "Options":                  {"de": "Optionen",                  "es": "Opciones",                   "fr": "Options",                    "ja": "オプション",             "pt_BR": "Opções",                      "ru": "Параметры",                  "zh_CN": "选项"},
    "Draw cut marks":           {"de": "Schnittmarken zeichnen",    "es": "Dibujar marcas de corte",    "fr": "Afficher les repères de coupe","ja": "切り取りマークを表示",   "pt_BR": "Desenhar marcas de corte",    "ru": "Показывать метки обрезки",   "zh_CN": "显示裁切标记"},
    "Preview…":                 {"de": "Vorschau …",                "es": "Vista previa…",              "fr": "Aperçu…",                    "ja": "プレビュー…",            "pt_BR": "Visualizar…",                 "ru": "Предпросмотр…",              "zh_CN": "预览…"},
    "Export as PDF…":           {"de": "Als PDF exportieren …",     "es": "Exportar como PDF…",         "fr": "Exporter en PDF…",           "ja": "PDFとしてエクスポート…", "pt_BR": "Exportar como PDF…",          "ru": "Экспортировать в PDF…",      "zh_CN": "导出为 PDF…"},
    "Print…":                   {"de": "Drucken …",                 "es": "Imprimir…",                  "fr": "Imprimer…",                  "ja": "印刷…",                  "pt_BR": "Imprimir…",                   "ru": "Печать…",                    "zh_CN": "打印…"},
    "Cancel":                   {"de": "Abbrechen",                 "es": "Cancelar",                   "fr": "Annuler",                    "ja": "キャンセル",             "pt_BR": "Cancelar",                    "ru": "Отмена",                     "zh_CN": "取消"},
    "Save PDF":                 {"de": "PDF speichern",             "es": "Guardar PDF",                "fr": "Enregistrer le PDF",         "ja": "PDFを保存",              "pt_BR": "Salvar PDF",                  "ru": "Сохранить PDF",              "zh_CN": "保存 PDF"},
    "PDF files (*.pdf)":        {"de": "PDF-Dateien (*.pdf)",       "es": "Archivos PDF (*.pdf)",       "fr": "Fichiers PDF (*.pdf)",       "ja": "PDFファイル (*.pdf)",    "pt_BR": "Arquivos PDF (*.pdf)",        "ru": "Файлы PDF (*.pdf)",          "zh_CN": "PDF 文件 (*.pdf)"},
    "PDF saved:\n{path}":       {"de": "PDF gespeichert:\n{path}",  "es": "PDF guardado:\n{path}",      "fr": "PDF enregistré :\n{path}",   "ja": "PDFを保存しました：\n{path}", "pt_BR": "PDF salvo:\n{path}",         "ru": "PDF сохранён:\n{path}",      "zh_CN": "PDF 已保存：\n{path}"},

    # ── PrintPreviewDialog ─────────────────────────────────────────────────
    "Print Preview":            {"de": "Druckvorschau",             "es": "Vista previa de impresión",  "fr": "Aperçu avant impression",    "ja": "印刷プレビュー",         "pt_BR": "Visualização de impressão",   "ru": "Предпросмотр печати",        "zh_CN": "打印预览"},
    "Side":                     {"de": "Seite",                     "es": "Cara",                       "fr": "Face",                       "ja": "面",                     "pt_BR": "Lado",                        "ru": "Сторона",                    "zh_CN": "面"},
    "Duplex":                   {"de": "Duplex",                    "es": "Dúplex",                     "fr": "Recto-verso",                "ja": "両面",                   "pt_BR": "Duplex",                      "ru": "Двусторонняя",               "zh_CN": "双面"},
    "Long edge":                {"de": "Lange Seite",               "es": "Borde largo",                "fr": "Grand côté",                 "ja": "長辺とじ",               "pt_BR": "Borda longa",                 "ru": "Длинная сторона",            "zh_CN": "长边"},
    "Short edge":               {"de": "Kurze Seite",               "es": "Borde corto",                "fr": "Petit côté",                 "ja": "短辺とじ",               "pt_BR": "Borda curta",                 "ru": "Короткая сторона",           "zh_CN": "短边"},
    "Binding edge:":            {"de": "Binderand:",                "es": "Borde de encuadernación:",   "fr": "Bord de reliure :",          "ja": "とじ方向：",             "pt_BR": "Margem de encadernação:",     "ru": "Корешковое поле:",           "zh_CN": "装订边："},
    "Cut marks":                {"de": "Schnittmarken",             "es": "Marcas de corte",            "fr": "Repères de coupe",           "ja": "切り取りマーク",         "pt_BR": "Marcas de corte",             "ru": "Метки обрезки",              "zh_CN": "裁切标记"},
    "Zoom:":                    {"de": "Zoom:",                     "es": "Zoom:",                      "fr": "Zoom :",                     "ja": "ズーム：",               "pt_BR": "Zoom:",                       "ru": "Масштаб:",                   "zh_CN": "缩放："},
    "Print / Export…":          {"de": "Drucken / Exportieren …",   "es": "Imprimir / Exportar…",       "fr": "Imprimer / Exporter…",       "ja": "印刷 / エクスポート…",   "pt_BR": "Imprimir / Exportar…",        "ru": "Печать / Экспорт…",          "zh_CN": "打印 / 导出…"},
    "{w}×{h} mm  |  {slots} slots/page  |  {cards} card(s)  |  {pages} page(s)": {"de": "{w}×{h} mm  |  {slots} Slots/Seite  |  {cards} Karte(n)  |  {pages} Seite(n)", "es": "{w}×{h} mm  |  {slots} huecos/página  |  {cards} tarjeta(s)  |  {pages} página(s)", "fr": "{w}×{h} mm  |  {slots} emplacements/page  |  {cards} carte(s)  |  {pages} page(s)", "ja": "{w}×{h} mm  |  {slots} スロット/ページ  |  {cards} 枚  |  {pages} ページ", "pt_BR": "{w}×{h} mm  |  {slots} posições/página  |  {cards} cartão(ões)  |  {pages} página(s)", "ru": "{w}×{h} мм  |  {slots} слотов/стр.  |  {cards} карт.  |  {pages} стр.", "zh_CN": "{w}×{h} mm  |  {slots} 个位置/页  |  {cards} 张名片  |  {pages} 页"},

    # ── PropertiesPanel ────────────────────────────────────────────────────
    "PROPERTIES":               {"de": "EIGENSCHAFTEN",             "es": "PROPIEDADES",                "fr": "PROPRIÉTÉS",                 "ja": "プロパティ",             "pt_BR": "PROPRIEDADES",                "ru": "СВОЙСТВА",                   "zh_CN": "属性"},
    "No element\nselected":     {"de": "Kein Element\nausgewählt",  "es": "Ningún elemento\nseleccionado","fr": "Aucun élément\nsélectionné", "ja": "要素が\n選択されていません","pt_BR": "Nenhum elemento\nselecionado","ru": "Элемент\nне выбран",         "zh_CN": "未选择\n任何元素"},
    "Position & Size":          {"de": "Position & Größe",          "es": "Posición y tamaño",          "fr": "Position et taille",         "ja": "位置とサイズ",           "pt_BR": "Posição e tamanho",           "ru": "Положение и размер",         "zh_CN": "位置和大小"},
    "X:":                       {"de": "X:",                        "es": "X:",                         "fr": "X :",                        "ja": "X：",                    "pt_BR": "X:",                          "ru": "X:",                         "zh_CN": "X："},
    "Y:":                       {"de": "Y:",                        "es": "Y:",                         "fr": "Y :",                        "ja": "Y：",                    "pt_BR": "Y:",                          "ru": "Y:",                         "zh_CN": "Y："},
    "Rotation:":                {"de": "Rotation:",                 "es": "Rotación:",                  "fr": "Rotation :",                 "ja": "回転：",                 "pt_BR": "Rotação:",                    "ru": "Поворот:",                   "zh_CN": "旋转："},
    "Font:":                    {"de": "Schrift:",                  "es": "Fuente:",                    "fr": "Police :",                   "ja": "フォント：",             "pt_BR": "Fonte:",                      "ru": "Шрифт:",                     "zh_CN": "字体："},
    "Size:":                    {"de": "Größe:",                    "es": "Tamaño:",                    "fr": "Taille :",                   "ja": "サイズ：",               "pt_BR": "Tamanho:",                    "ru": "Размер:",                    "zh_CN": "大小："},
    "Style:":                   {"de": "Stil:",                     "es": "Estilo:",                    "fr": "Style :",                    "ja": "スタイル：",             "pt_BR": "Estilo:",                     "ru": "Начертание:",                "zh_CN": "样式："},
    "Color:":                   {"de": "Farbe:",                    "es": "Color:",                     "fr": "Couleur :",                  "ja": "色：",                   "pt_BR": "Cor:",                        "ru": "Цвет:",                      "zh_CN": "颜色："},
    "Alignment:":               {"de": "Ausrichtung:",              "es": "Alineación:",                "fr": "Alignement :",               "ja": "配置：",                 "pt_BR": "Alinhamento:",                "ru": "Выравнивание:",              "zh_CN": "对齐方式："},
    "Image":                    {"de": "Bild",                      "es": "Imagen",                     "fr": "Image",                      "ja": "画像",                   "pt_BR": "Imagem",                      "ru": "Изображение",                "zh_CN": "图片"},
    "Browse…":                  {"de": "Durchsuchen …",             "es": "Examinar…",                  "fr": "Parcourir…",                 "ja": "参照…",                  "pt_BR": "Procurar…",                   "ru": "Обзор…",                     "zh_CN": "浏览…"},
    "File:":                    {"de": "Datei:",                    "es": "Archivo:",                   "fr": "Fichier :",                  "ja": "ファイル：",             "pt_BR": "Arquivo:",                    "ru": "Файл:",                      "zh_CN": "文件："},
    "Keep aspect ratio":        {"de": "Seitenverhältnis beibehalten","es": "Mantener proporciones",    "fr": "Conserver les proportions",  "ja": "縦横比を維持",           "pt_BR": "Manter proporções",           "ru": "Сохранять пропорции",        "zh_CN": "保持宽高比"},
    "Shape / Border":           {"de": "Form / Rahmen",             "es": "Forma / Borde",              "fr": "Forme / Bordure",            "ja": "形状 / 枠線",            "pt_BR": "Forma / Borda",               "ru": "Фигура / Рамка",             "zh_CN": "形状 / 边框"},
    "Fill color:":              {"de": "Füllfarbe:",                "es": "Color de relleno:",          "fr": "Couleur de remplissage :",   "ja": "塗りつぶし色：",         "pt_BR": "Cor de preenchimento:",       "ru": "Цвет заливки:",              "zh_CN": "填充色："},
    "Border color:":            {"de": "Rahmenfarbe:",              "es": "Color de borde:",            "fr": "Couleur de bordure :",       "ja": "枠線の色：",             "pt_BR": "Cor da borda:",               "ru": "Цвет рамки:",                "zh_CN": "边框颜色："},
    "Border width:":            {"de": "Rahmenbreite:",             "es": "Grosor del borde:",          "fr": "Épaisseur de la bordure :",  "ja": "枠線の太さ：",           "pt_BR": "Espessura da borda:",         "ru": "Толщина рамки:",             "zh_CN": "边框宽度："},
    "Content:":                 {"de": "Inhalt:",                   "es": "Contenido:",                 "fr": "Contenu :",                  "ja": "コンテンツ：",           "pt_BR": "Conteúdo:",                   "ru": "Содержимое:",                "zh_CN": "内容："},
    "Icon":                     {"de": "Symbol",                    "es": "Icono",                      "fr": "Icône",                      "ja": "アイコン",               "pt_BR": "Ícone",                       "ru": "Значок",                     "zh_CN": "图标"},
    "Choose Icon…":             {"de": "Symbol wählen …",           "es": "Elegir icono…",              "fr": "Choisir une icône…",         "ja": "アイコンを選択…",        "pt_BR": "Escolher ícone…",             "ru": "Выбрать значок…",            "zh_CN": "选择图标…"},
    "Icon:":                    {"de": "Symbol:",                   "es": "Icono:",                     "fr": "Icône :",                    "ja": "アイコン：",             "pt_BR": "Ícone:",                      "ru": "Значок:",                    "zh_CN": "图标："},
    "Miscellaneous":            {"de": "Sonstiges",                 "es": "Varios",                     "fr": "Divers",                     "ja": "その他",                 "pt_BR": "Outros",                      "ru": "Прочее",                     "zh_CN": "其他"},
    "Visible":                  {"de": "Sichtbar",                  "es": "Visible",                    "fr": "Visible",                    "ja": "表示",                   "pt_BR": "Visível",                     "ru": "Видимый",                    "zh_CN": "可见"},
    "Locked":                   {"de": "Gesperrt",                  "es": "Bloqueado",                  "fr": "Verrouillé",                 "ja": "ロック",                 "pt_BR": "Bloqueado",                   "ru": "Заблокирован",               "zh_CN": "锁定"},

    # ── PropertiesPanel -- Text subpanel ────────────────────────────────────
    "Text:":                    {"de": "Text:",                     "es": "Texto:",                     "fr": "Texte :",                    "ja": "テキスト：",             "pt_BR": "Texto:",                      "ru": "Текст:",                     "zh_CN": "文字："},
    "QR Code":                  {"de": "QR-Code",                   "es": "Código QR",                  "fr": "Code QR",                    "ja": "QRコード",               "pt_BR": "Código QR",                   "ru": "QR-код",                     "zh_CN": "二维码"},
}

# ---------------------------------------------------------------------------

LANG_META = {
    "de":    ("de_DE", "cardforge_de.ts"),
    "es":    ("es_ES", "cardforge_es.ts"),
    "fr":    ("fr_FR", "cardforge_fr.ts"),
    "ja":    ("ja_JP", "cardforge_ja.ts"),
    "pt_BR": ("pt_BR", "cardforge_pt_BR.ts"),
    "ru":    ("ru_RU", "cardforge_ru.ts"),
    "zh_CN": ("zh_CN", "cardforge_zh_CN.ts"),
}

I18N_DIR = os.path.join(
    os.path.dirname(__file__), "..", "src", "cardforge", "i18n"
)


def fill_ts(lang: str) -> None:
    _, filename = LANG_META[lang]
    path = os.path.join(I18N_DIR, filename)

    ET.register_namespace("", "")
    tree = ET.parse(path)
    root = tree.getroot()

    filled = 0
    skipped = 0

    for message in root.iter("message"):
        src_el = message.find("source")
        tr_el  = message.find("translation")
        if src_el is None or tr_el is None:
            continue

        src = src_el.text or ""
        translation = T.get(src, {}).get(lang)

        if translation is not None:
            tr_el.text = translation
            # Remove type="unfinished" once translated
            if "type" in tr_el.attrib:
                del tr_el.attrib["type"]
            filled += 1
        else:
            skipped += 1

    # Write with XML declaration and proper encoding
    tree.write(path, encoding="utf-8", xml_declaration=True)

    # ET strips the DOCTYPE -- restore it
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    doctype = '<!DOCTYPE TS>\n'
    if doctype not in content:
        content = content.replace("?>\n", "?>\n" + doctype, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"[{lang:6s}]  filled={filled:3d}  skipped (no translation)={skipped:3d}  → {filename}")


def main() -> None:
    for lang in LANG_META:
        fill_ts(lang)


if __name__ == "__main__":
    main()
