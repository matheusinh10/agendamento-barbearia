# Agendamento para Barbearia
PROJETO DE EXTENSÃO EM WEB BACK-END 2026/2 — Matheus Passos de Lima (ADS, turma SM262424)

Back-end em Python (FastAPI + SQLite) para agendamento em uma barbearia, com controle de conflito de horário,
registro de faltas, lista de espera (com link de WhatsApp) e relatório de renda perdida.

## Como rodar
1. Instale o Python 3.10+
2. `pip install -r requirements.txt`
3. `python -m uvicorn main:app --reload`
4. Abra http://127.0.0.1:8000/docs (documentação OpenAPI/Swagger interativa)

O banco `barbearia.db` é criado automaticamente na primeira execução.

### Com Docker (opcional)
```
docker build -t barbearia .
docker run -p 8000:8000 barbearia
```

## Testes automatizados
```
pip install -r requirements-dev.txt
python -m pytest -v
```
Cobrem: conflito de horário (409), expediente, passado, fuso `Z`, horários disponíveis, remarcação/cancelamento,
falta + encaixe via WhatsApp, lista de espera e relatório de renda perdida.

## Roteiro de demonstração
1. POST /barbeiros, /servicos e /clientes
2. POST /agendamentos (ex.: `"inicio": "2026-12-01T14:00:00"`)
3. Repita às 14:20 para ver o erro 409 (conflito)
4. POST /lista-espera e depois PATCH /agendamentos/1/faltou (gera o link do WhatsApp)
5. GET /relatorios/faltas
6. GET /healthz

## Documentação
- [Documentação técnica da entrega 3 (PDF)](docs/Entrega3_Melhorias_Agendamento_Barbearia.pdf)
- [CHANGELOG](CHANGELOG.md)
