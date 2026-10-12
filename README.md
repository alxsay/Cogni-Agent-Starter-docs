# Cogni Agent Starter — documentação

Site estático da documentação do Cogni Agent Starter, publicado em
<https://alxsay.github.io/Cogni-Agent-Starter-docs/>.

Este repositório contém **só** a documentação pública. A fonte de verdade é o repositório privado
do starter (`docs/public/` e `mkdocs.yml`); alterações devem ser feitas lá e copiadas para cá.

## Build local

```bash
uv run --no-project --python 3.12 --with-requirements requirements-docs.txt mkdocs serve
```

## Publicação

Todo push em `main` gera o site com `mkdocs build --strict` e publica no GitHub Pages
(`.github/workflows/pages.yml`).
