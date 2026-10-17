# Agendamento para Barbearia
PROJETO DE EXTENSÃO EM WEB BACK-END 2026/2

Back-end em Python (FastAPI + SQLite) para agendamento em uma barbearia, com controle
de conflito de horário, registro de faltas, lista de espera e relatório de renda perdida.

## Como rodar
1. Instale o Python 3.10+
2. pip install -r requirements.txt
3. python -m uvicorn main:app --reload
4. Abra http://127.0.0.1:8000/docs

## Roteiro de teste
1. POST /barbeiros, /servicos e /clientes
2. POST /agendamentos (ex.: "inicio": "2026-10-20T14:00:00")
3. Repita às 14:20 para ver o erro 409 (conflito)
4. POST /lista-espera e depois PATCH /agendamentos/1/faltou (gera o link do WhatsApp)
5. GET /relatorios/faltas
