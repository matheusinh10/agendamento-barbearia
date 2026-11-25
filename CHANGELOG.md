# Changelog
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.1.0] - 2026-11
### Adicionado
- Endpoint `GET /healthz` para verificação de integridade (API + banco).
- Testes automatizados com pytest (17 cenários) e banco temporário por teste.
- `Dockerfile` e `.dockerignore` para execução em contêiner.
- `requirements-dev.txt` e `.gitignore`.

## [1.0.1] - 2026-10
### Corrigido
- Erro 500 ao enviar horário com fuso (sufixo `Z`); o fuso agora é removido antes da comparação.

## [1.0.0] - 2026-10
### Adicionado
- Cadastro de barbeiros, serviços e clientes.
- Agendamento com cálculo de fim, bloqueio de conflito (409), expediente 09:00–19:00 e bloqueio de passado.
- Horários disponíveis, remarcação e cancelamento.
- Registro de falta, lista de espera, link de WhatsApp para encaixe e relatório de renda perdida.
