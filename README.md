# Instagram Scraper Agent

Ferramenta de linha de comando para coletar publicações e mídias de perfis públicos do Instagram. Autentica via API privada do `instagrapi`, pagina os posts com cursor, baixa mídias em paralelo com jitter de rate limit e persiste tudo em JSON estruturado por perfil.

---

## Sumário

- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Arquitetura](#arquitetura)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [Modelos de Dados](#modelos-de-dados)
- [Saída](#saída)
- [Testes](#testes)
- [Decisões Técnicas](#decisões-técnicas)
- [Limitações e Avisos](#limitações-e-avisos)

---

## Requisitos

- Python 3.12+
- Conta Instagram válida (usada para autenticação via API privada)
- Variáveis de ambiente configuradas no `.env`

---

## Instalação

```bash
git clone <repo>
cd instagram_agents_groq
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```env
GROQ_API_KEY=sua_chave_groq
INSTAGRAM_USERNAME=seu_usuario_instagram
INSTAGRAM_PASSWORD=sua_senha_instagram
OUTPUT_DIR=output          # opcional, padrão: output
LOG_LEVEL=INFO             # opcional, padrão: INFO
```

> **Atenção:** nunca versione o `.env`. Adicione ao `.gitignore`.

---

## Uso

```bash
python main.py <username> [max_posts] [download_media] [force_download]
```

| Parâmetro        | Tipo    | Padrão  | Descrição                                                              |
|------------------|---------|---------|------------------------------------------------------------------------|
| `username`       | `str`   | —       | Username do perfil alvo (obrigatório)                                  |
| `max_posts`      | `int`   | `0`     | Limite de posts. `0` = busca todos sem limite                          |
| `download_media` | `bool`  | `true`  | Se `true`, baixa as mídias (imagens/vídeos) de cada post               |
| `force_download` | `bool`  | `false` | Se `true`, re-baixa mídias mesmo que já existam localmente             |

### Exemplos

```bash
# Busca todos os posts, baixa só o que ainda não foi baixado
python main.py cris.agra_distribuidora

# Busca os 10 posts mais recentes, sem baixar mídias
python main.py cris.agra_distribuidora 10 false

# Busca 5 posts e força re-download de todas as mídias
python main.py cris.agra_distribuidora 5 true true
```

---

## Arquitetura

### Visão Geral

```
main.py
  └── bootstrap(username)          # configura serviços e injeta dependências
  └── OrchestratorAgent.run()      # coordena o pipeline completo
        ├── ProfileAgent.run()     # coleta dados do perfil
        ├── ScraperAgent.run()     # coleta posts com paginação
        ├── MediaAgent.run()       # baixa mídias em paralelo
        └── StorageService.save()  # persiste JSON em disco
```

### Camadas

```
┌─────────────────────────────────────────────────────┐
│                     main.py                         │  Entrypoint / Bootstrap
├─────────────────────────────────────────────────────┤
│                    agents/                          │  Orquestração
│  OrchestratorAgent  ProfileAgent  ScraperAgent      │
│  MediaAgent                                         │
├─────────────────────────────────────────────────────┤
│                   services/                         │  Lógica de negócio
│  InstagramService  MediaService  StorageService     │
├─────────────────────────────────────────────────────┤
│                    models/                          │  Entidades de domínio
│  InstagramProfile  InstagramPost  MediaItem         │
│  MediaType                                          │
├─────────────────────────────────────────────────────┤
│                     utils/                          │  Infraestrutura
│  config.py  logger.py  rate_limiter.py              │
└─────────────────────────────────────────────────────┘
```

### Fluxo de Execução

```
1. bootstrap(username)
   ├── Configura logger (stdout + arquivo rotativo)
   ├── Cria diretórios output/{username}/posts/
   ├── InstagramService.authenticate()
   │     ├── Se .instagram_session.json existe → load_settings + account_info()
   │     │     ├── OK → sessão restaurada (sem novo login)
   │     │     └── Falha → reseta Client, faz login completo
   │     └── Senão → login + dump_settings (salva sessão)
   └── Injeta serviços via init_tools()

2. OrchestratorAgent.run(username, max_posts, download_media, force_download)
   │
   ├── ProfileAgent.run(username)
   │     └── InstagramService.get_profile(username)
   │           └── user_info_by_username_v1()  [API privada]
   │
   ├── ScraperAgent.run(username, max_posts)
   │     └── InstagramService.get_posts(username, max_posts)
   │           └── loop de paginação com user_medias_paginated_v1()
   │                 ├── Página 1 → posts[0..32]
   │                 ├── jitter_sleep(2s–5s)
   │                 ├── Página 2 → posts[33..65]
   │                 ├── jitter_sleep(2s–5s)
   │                 └── ... até cursor vazio ou max_posts atingido
   │
   ├── [se download_media] MediaAgent.run(posts_json, force)
   │     └── ThreadPoolExecutor(max_workers=3)
   │           └── Para cada post (em paralelo):
   │                 ├── jitter_sleep(1s–4s)   [antes de cada download]
   │                 └── MediaService.download_post_media(post, force)
   │                       └── Para cada mídia do post:
   │                             ├── Se arquivo existe e force=False → pula
   │                             └── Senão → httpx.Client.get(url) → salva
   │
   └── StorageService.save(profile, posts)
         └── output/{username}/profile_data.json
```

---

## Estrutura de Diretórios

```
instagram_agents_groq/
├── agents/
│   ├── base_agent.py          # ABC base (usado pelo MediaAgent)
│   ├── media_agent.py         # Download paralelo de mídias com jitter
│   ├── orchestrator_agent.py  # Coordena o pipeline completo
│   ├── profile_agent.py       # Coleta dados do perfil
│   └── scraper_agent.py       # Coleta posts com paginação
├── models/
│   ├── post.py                # InstagramPost, MediaItem, MediaType
│   └── profile.py             # InstagramProfile
├── services/
│   ├── instagram_service.py   # Autenticação, perfil e posts via instagrapi
│   ├── media_service.py       # Download de arquivos via httpx
│   └── storage_service.py     # Persistência em JSON
├── tests/
│   ├── test_agents_direct.py          # ProfileAgent, ScraperAgent, datetime
│   ├── test_instagram_service_session.py  # Sessão persistente
│   ├── test_media_agent.py            # Download paralelo, isolamento de erros
│   ├── test_media_service.py          # Download, skip, force, paralelismo
│   ├── test_new_features.py           # Output por username, paginação, force
│   ├── test_rate_limiter.py           # jitter_sleep, delays entre páginas/posts
│   └── test_storage_service.py        # Serialização correta via to_dict()
├── tools/
│   └── instagram_tools.py     # Service locator + tools agno (legado)
├── utils/
│   ├── config.py              # Settings via pydantic-settings
│   ├── logger.py              # Configuração do loguru
│   └── rate_limiter.py        # jitter_sleep para evitar rate limit
├── .env                       # Credenciais (não versionar)
├── .instagram_session.json    # Sessão salva (gerado automaticamente)
├── main.py                    # Entrypoint
└── requirements.txt
```

---

## Modelos de Dados

### `InstagramProfile`

| Campo             | Tipo       | Descrição                          |
|-------------------|------------|------------------------------------|
| `username`        | `str`      | Username do perfil                 |
| `user_id`         | `str`      | ID numérico do usuário             |
| `full_name`       | `str`      | Nome completo                      |
| `bio`             | `str`      | Biografia                          |
| `profile_url`     | `str`      | URL do perfil                      |
| `profile_pic_url` | `str`      | URL da foto de perfil              |
| `followers_count` | `int`      | Número de seguidores               |
| `following_count` | `int`      | Número de seguindo                 |
| `posts_count`     | `int`      | Total de publicações               |
| `is_private`      | `bool`     | Perfil privado                     |
| `is_verified`     | `bool`     | Conta verificada                   |
| `external_url`    | `str\|None`| Link externo na bio                |
| `scraped_at`      | `datetime` | Timestamp UTC da coleta            |

### `InstagramPost`

| Campo             | Tipo            | Descrição                          |
|-------------------|-----------------|------------------------------------|
| `post_id`         | `str`           | ID numérico da publicação          |
| `shortcode`       | `str`           | Código curto (usado na URL)        |
| `post_url`        | `str\|None`     | URL completa da publicação         |
| `caption`         | `str`           | Legenda                            |
| `media_type`      | `MediaType`     | `image`, `video`, `carousel`, `reel` |
| `media_items`     | `list[MediaItem]` | Mídias da publicação             |
| `likes_count`     | `int`           | Número de curtidas                 |
| `comments_count`  | `int`           | Número de comentários              |
| `taken_at`        | `datetime\|None`| Data de publicação                 |
| `local_dir`       | `str\|None`     | Diretório local das mídias         |

### `MediaItem`

| Campo        | Tipo        | Descrição                              |
|--------------|-------------|----------------------------------------|
| `media_id`   | `str`       | ID da mídia                            |
| `url`        | `str`       | URL original (CDN do Instagram)        |
| `media_type` | `MediaType` | Tipo da mídia                          |
| `local_path` | `str\|None` | Caminho local após download            |

---

## Saída

### Estrutura de diretórios gerada

```
output/
└── {username}/
    ├── profile_data.json
    └── posts/
        ├── {post_id}/
        │   ├── {media_id}_0.jpg
        │   └── {media_id}_1.jpg   # carrosséis têm múltiplos arquivos
        └── {post_id}/
            └── {media_id}_0.mp4   # vídeos e reels
```

### Estrutura do `profile_data.json`

```json
{
  "profile": {
    "user_id": "123456789",
    "username": "cris.agra_distribuidora",
    "full_name": "Cris Agra Distribuidora",
    "bio": "...",
    "profile_url": "https://www.instagram.com/cris.agra_distribuidora/",
    "profile_pic_url": "https://...",
    "external_url": null,
    "followers_count": 1500,
    "following_count": 300,
    "posts_count": 87,
    "is_private": false,
    "is_verified": false,
    "scraped_at": "2026-03-26T13:25:09+00:00"
  },
  "posts": [
    {
      "id_pub": "3860595998585799491",
      "shortcode": "ABC123",
      "post_url": "https://www.instagram.com/p/ABC123/",
      "caption": "Legenda da publicação...",
      "media_type": "image",
      "likes_count": 42,
      "comments_count": 5,
      "taken_at": "2026-03-25T10:00:00+00:00",
      "local_dir": "output/cris.agra_distribuidora/posts/3860595998585799491",
      "media": [
        {
          "id": "3860595998585799491",
          "link": "https://cdninstagram.com/...",
          "type": "image",
          "local_path": "output/cris.agra_distribuidora/posts/3860595998585799491/3860595998585799491_0.jpg"
        }
      ]
    }
  ]
}
```

---

## Testes

```bash
# Executar todos os testes
python -m pytest tests/ -v

# Executar um arquivo específico
python -m pytest tests/test_rate_limiter.py -v

# Com cobertura (requer pytest-cov)
python -m pytest tests/ --cov=. --cov-report=term-missing
```

### Suíte atual: 52 testes

| Arquivo                              | Testes | O que cobre                                          |
|--------------------------------------|--------|------------------------------------------------------|
| `test_agents_direct.py`              | 10     | ProfileAgent, ScraperAgent sem LLM, timezone-aware   |
| `test_instagram_service_session.py`  | 4      | Sessão persistente, re-login, falha de autenticação  |
| `test_media_agent.py`                | 4      | Download paralelo, isolamento de erros por post      |
| `test_media_service.py`              | 9      | Download, skip, force, extensões, paralelismo        |
| `test_new_features.py`               | 12     | Output por username, paginação, force_download       |
| `test_rate_limiter.py`               | 7      | jitter_sleep, delays entre páginas e posts           |
| `test_storage_service.py`            | 6      | Serialização via to_dict(), UTF-8, estrutura JSON    |

---

## Decisões Técnicas

### Sessão persistente (`.instagram_session.json`)

O `instagrapi` salva cookies e tokens de sessão em JSON. Na inicialização, o sistema tenta restaurar a sessão com `account_info()` (rota privada leve). Se a sessão estiver inválida, reseta o `Client` e faz novo login. Em caso de falha total, remove o arquivo corrompido automaticamente.

**Benefício:** evita login completo a cada execução, reduzindo drasticamente o risco de `ChallengeRequired`.

### API privada exclusiva (`_v1`)

Todas as chamadas ao Instagram usam rotas da API privada autenticada (`user_info_by_username_v1`, `user_medias_paginated_v1`), evitando as rotas públicas GQL (`/web_profile_info`) que retornam `429 Too Many Requests` com frequência.

### Paginação explícita com cursor

`get_posts` implementa o loop de paginação manualmente usando `user_medias_paginated_v1`, que retorna `(List[Media], next_cursor)`. Isso permite:
- `max_posts=0` → busca todas as páginas até cursor vazio
- `max_posts=N` → para assim que N posts são coletados, sem buscar páginas extras
- Delay com jitter entre páginas para não sobrecarregar a API

### Jitter de rate limit

`jitter_sleep(min_s, max_s)` usa `random.uniform` para gerar delays não-determinísticos. Delays fixos são detectados como padrão de bot. Aplicado em dois pontos:

| Ponto                        | Range    | Motivo                                      |
|------------------------------|----------|---------------------------------------------|
| Entre páginas de paginação   | 2s – 5s  | Requisições à API privada do Instagram      |
| Antes de cada download       | 1s – 4s  | Requisições ao CDN, menos restritivas       |

### Download paralelo com workers limitados

`MediaAgent` usa `ThreadPoolExecutor(max_workers=3)`. O jitter por worker garante que as 3 threads não disparem simultaneamente — cada uma dorme um tempo diferente antes de iniciar. Workers limitados a 3 (vs. 5 original) para menor pressão simultânea.

### `force_download`

`MediaService._download_file` verifica `file_path.exists() and not force`. Com `force=False` (padrão), arquivos já baixados são pulados — idempotente e eficiente para re-execuções. Com `force=True`, re-baixa tudo independente do estado local.

### Output por username

Cada perfil tem seu próprio diretório isolado em `output/{username}/`. Permite coletar múltiplos perfis sem conflito de arquivos.

### `to_dict()` nos modelos

`StorageService.save` chama `profile.to_dict()` e `post.to_dict()` explicitamente. O uso de `__dict__` (abordagem anterior) serializava objetos internos como `MediaItem` e `datetime` sem conversão, causando `TypeError` no `json.dumps`.

---

## Limitações e Avisos

**Termos de Serviço do Instagram**
Este projeto usa a API privada do Instagram via `instagrapi`. O uso de automação viola os Termos de Serviço do Instagram. Use com responsabilidade e apenas em contas e perfis que você tem permissão para acessar.

**`ChallengeRequired`**
O Instagram pode exigir verificação de segurança (e-mail/SMS) quando detecta atividade suspeita — especialmente após múltiplos logins em sequência. Se isso ocorrer:
1. Acesse o Instagram pelo app ou browser com a conta configurada
2. Complete o desafio de segurança
3. Delete o arquivo `.instagram_session.json`
4. Execute novamente

**Perfis privados**
O sistema não consegue coletar posts de perfis privados a menos que a conta autenticada siga o perfil alvo.

**Rate limit**
Mesmo com jitter, contas com muitas execuções em curto período podem ser temporariamente bloqueadas. Recomenda-se não executar mais de uma vez por hora para o mesmo perfil.
