# dev-loop-kit 1.14.0 — plateau y stop-signal en readiness (2026-07-03)

Quinta mejora del backlog PragProg (M6 de `docs/analisis-pragmatic-programmer.md`;
Topic 37 *"Listen to Your Lizard Brain"* + Topic 5 *"Know When to Stop"*).
La convergencia per-tool existía, pero el engine nunca decía las dos cosas que
un senior sí dice: "esto no está convergiendo — el problema es de diseño" y
"esto ya está — cortá". **ADVISORY puro: recomienda, jamás gatea.**
Smoke suite: 89/89.

## La idea

- **stall-check**: findings gateados por CICLO de agente (suma sobre las tools
  del ciclo). Si los últimos 3 ciclos muestran la serie plana o SUBIENDO — y
  todavía hay findings — iterar más no está acercando la solución: el engine
  deja de sugerir implícitamente "seguí iterando" y recomienda **volver a
  ADR / re-planear con el humano**. Una serie bajando es progreso y no dispara.
  Con `qa_tools_order` configurado solo cuentan ciclos **COMPLETOS** (todas las
  tools logueadas) — un ciclo a medio correr suma parcial y podría enmascarar
  o inventar el stall (hallazgo del review fresco, aplicado).
- **stop-signal**: todos los repos convergieron, cero caps activos y cero
  findings gateados abiertos — no queda ningún fact bloqueante. Lo que falte
  es deuda medible (coverage/acceptance), no findings: **candidato a cortar e
  ir a PR**, decisión del humano.

## Engine (qa_ledger.py)

- `_stall_series()` / `_is_stalled()` (ventana `STALL_WINDOW = 3`, constante:
  es un advisory, no un gate parametrizable — cf. tensión ETC/M5, deliberado).
- `readiness`: JSON expone `advice: {stalled_repos, stop_signal}`; el texto
  imprime ambos avisos marcados "(advisory)".

## Smoke

- **T36**: serie 4→5→6 dispara stall · un ciclo 4 PARCIAL no contamina la
  serie · serie 5→3→1 (progreso) NO dispara · repo único convergido con cero
  facts bloqueantes emite `stop_signal: true`.

## Diferido consciente

- El stall mide findings gateados por ciclo, no el score de readiness
  persistido por iteración (el ledger no guarda score histórico — si algún
  día lo guarda, el detector puede leer el KPI directo).
