# 🧾 API OCR para Comprobantes de Pago

Este proyecto usa **FastAPI** para desarrollar una API que recibe comprobantes de pago (boletas, facturas, etc.), realiza reconocimiento óptico de caracteres (OCR) y extrae campos clave como RUC, monto total, fecha, etc.

---

## 🚀 Requisitos

Antes de comenzar, asegúrate de tener instalado en Windows:

- [Python 3.8 o superior](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)
- `pip` (se instala automáticamente con Python)

---

## ⚙️ Instalación en Windows

### 1. Clona el repositorio

```cmd
git clone https://github.com/tu_usuario/tu_repositorio.git
cd tu_repositorio
```

### 2. Crea y activa un entorno virtual
```cmd
python -m venv .venv
.venv\Scripts\activate
```
Asegúrate de ver que tu consola cambia a (.venv) al inicio de la línea, lo que indica que el entorno está activo.

### 3. Instala las dependencias
```cmd
pip install -r requirements.txt
```

### 4. Ejecutar el proyecto
Desde la raíz del proyecto (y con el entorno virtual activado), ejecuta:
```cmd
uvicorn app.main:app --reload
```