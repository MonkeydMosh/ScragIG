# IG Recon — Instagram Scraper con interfaz web

Extrae datos de Instagram usando **cookies de sesión**, sin Selenium ni BeautifulSoup.  
Backend en **FastAPI** + streaming por **SSE**. Frontend HTML/CSS/JS puro.

---

## Stack

| Capa       | Tecnología                              |
|------------|-----------------------------------------|
| HTTP       | `requests` (cookie auth)                |
| Backend    | FastAPI + uvicorn                       |
| Streaming  | Server-Sent Events (SSE)                |
| Frontend   | HTML/CSS/JS vanilla                     |
| Salida     | JSON descargable desde el navegador     |

---

## Instalación

```bash
pip install -r requirements.txt
```

---

## Cómo obtener las cookies

1. Abre [instagram.com](https://www.instagram.com) e inicia sesión
2. Abre DevTools → `F12`
3. **Chrome**: Application → Cookies → `https://www.instagram.com`  
   **Firefox**: Storage → Cookies → `https://www.instagram.com`
4. Copia los valores de `sessionid` y `csrftoken`

---

## Ejecutar

```bash
python app.py
# o
uvicorn app:app --reload --port 8000
```

Abre: [http://localhost:8000](http://localhost:8000)

---

## Funcionalidades

### Perfil
- Nombre, username, bio, tipo de cuenta
- Seguidores, siguiendo, posts
- Verificado / privado

### Following / Followers
- Lista completa con paginación automática
- Streaming en tiempo real (se va mostrando mientras llega)
- Filtro de búsqueda en tabla
- Desde cualquier usuario (público)

### Posts
- Últimos N posts del perfil objetivo
- Tipo (foto/video/carrusel), caption, likes, comentarios, vistas, fecha
- Botón para ver comentarios o likes de cada post directamente

### Comentarios
- Por media_id de cualquier post
- Autor, texto, likes, fecha

### Likes
- Lista de usuarios que dieron like a un post

### Descarga JSON
- Cualquier resultado se puede exportar con un clic

---

## Endpoints API

| Método | Ruta                    | Descripción                              |
|--------|-------------------------|------------------------------------------|
| GET    | `/api/profile`          | Info del perfil                          |
| GET    | `/api/stream/following` | SSE: lista de following                  |
| GET    | `/api/stream/followers` | SSE: lista de followers                  |
| GET    | `/api/stream/posts`     | SSE: posts del usuario                   |
| GET    | `/api/stream/comments`  | SSE: comentarios de un post              |
| GET    | `/api/likers`           | Lista de usuarios que likearon un post   |

Todos requieren `session_id` y `csrf_token` como query params.

---

## Estructura

```
igapp/
├── app.py          # FastAPI backend
├── instagram.py    # Cliente puro requests (lógica de scraping)
├── requirements.txt
└── templates/
    └── index.html  # Interfaz web completa
```
