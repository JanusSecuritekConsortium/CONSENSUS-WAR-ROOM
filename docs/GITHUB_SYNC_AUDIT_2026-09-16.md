# Auditoría de sincronización de CONSENSUS

Fecha: 16 de septiembre de 2026. Origen: `G:\CONSENSUS_SYSTEM`.
Repositorio: https://github.com/JanusSecuritekConsortium/CONSENSUS-WAR-ROOM

## Dictamen

El árbol local no estaba sincronizado con GitHub. Se ha preparado una rama de revisión `codex/sync-audit-20260916`, con los cambios locales separados en commits, fuentes del launcher, protección de datos y CHANGELOG. Integra el `main` remoto mediante merge sin conflictos. No es una release validada: la suite completa presenta fallos y no debe fusionarse a main todavía. El resultado de la publicación se registra en `RESULTADO.md`.

Se trabajó en una copia aislada: el árbol operativo de G: conserva sus archivos y sus cambios sin commit. Por tanto, publicar la rama de revisión respalda esos cambios en GitHub, pero no convierte el checkout operativo ni su main local en un árbol actualizado y limpio.

## Estado inicial comprobado contra GitHub

| Referencia | Commit | Situación |
|---|---|---|
| Rama activa local `codex/boot-refresh-fix` | `23749a2` | Sin upstream; no existía en GitHub |
| Rama local `codex/deterministic-arbiter-consensus` | `23749a2` | Un commit por delante de su remoto |
| Rama remota `codex/deterministic-arbiter-consensus` | `e98a3a4` | Analytics CSV y eventos API; aún no contenidos en main |
| `main` local | `86ea447` | 44 commits por detrás de origin/main |
| `main` remoto | `fed5386` | Merge del PR #8 |

Comparación de la rama activa con main remoto: 8 commits exclusivos de main y 2 exclusivos del lado local. Los 8 son commits de merge. De los 2 del lado local, `e98a3a4` ya estaba publicado en la otra rama; solo `23749a2` no era alcanzable desde las ramas remotas verificadas. No hay que confundir «no contenido en main» con «no pusheado».

GitHub tenía dos ramas, cero tags y cero releases (consulta de referencias y API pública de releases). Tampoco había tags locales. `pyproject.toml` y CHANGELOG declaran 8.0.0: existe versión declarada, pero no una release/tag reproducible que la respalde.

## Cambios locales

617 archivos bajo seguimiento; 17 modificados y 6 nuevos. Lista exacta en `audit-inventory.json`.

| Grupo | Archivos y comportamiento |
|---|---|
| Empaquetado | `CONSENSUS.spec`, `build_exe.py`, `core/prompting/assembler.py`, `tools/boot.py` y test nuevo: incluir perfiles de monolitos y resolverlos desde los recursos empaquetados |
| AURELIUS | Servidor MCP, informes, `aurelius_memory.py`, documentación y tests: recordar/consultar/olvidar hechos mediante revisiones SQLite; selección y deduplicación de noticias; consulta de tareas abiertas |
| GUI y temas | `ui/flet_app.py`, `ui/components/header.py`, `ui/assets/registry.py`, boot y tests: refresco parcial, bloqueo de render, foco, botones de footer, cierre de diagnóstico, geometría de logos y arranque por lotes |

El commit previo `23749a2` modifica 826 archivos: 852 inserciones y 321.717 eliminaciones. Incluye portabilidad Linux/audio, informes AURELIUS, reorganización de documentación y retirada de 714 archivos de `reports/`, 42 de `archive/` y 27 de `future_implementations/`. La eliminación del árbol versionado no elimina copias operativas ignoradas ni purga el historial de GitHub. La ausencia del antiguo bot archivado rompe una prueba que todavía lo exige.

## Componentes solicitados

- **CONSENSUS:** el commit de analytics `e98a3a4` estaba en GitHub, pero no en main; la rama preparada lo conserva e integra main.
- **AURELIUS:** informes añadidos en el commit local previo; mejoras y memoria compartida aún sin commit. La nueva memoria accede a un pack de Msty Go en `%APPDATA%`; se versiona el código y las pruebas sintéticas, no la base de datos. No se abrió ni copió la base personal para esta auditoría. Su ruta actual es específica de Windows; no se certifica portabilidad Linux de esa integración.
- **MNEMOSYNE:** no se identificó un módulo o esquema explícito con ese nombre en el árbol revisado. Sí existen `core/memory/{store,session,context,retrieval}.py`, ya iguales a main, y la nueva memoria de AURELIUS. No hay evidencia para afirmar que un subsistema llamado MNEMOSYNE esté íntegramente publicado. La búsqueda no abarcó indiscriminadamente todos los discos ni datos personales.
- **MstyConsensusLauncher:** el directorio `G:\Tools\MstyConsensusLauncher` no tenía repositorio propio y CONSENSUS solo versionaba su documentación. Se incorporaron las fuentes C#, build, regresión, watchdog, ayuda de ventana, README y configuración de ejemplo en `tools/msty_launcher/`. Se excluyeron ejecutables, configuración operativa y salidas. No se ejecutaron scripts que alteran servicios, accesos directos o configuración. La etiqueta «release-stable v1.1.3» de su README es previa, no una validación nueva del binario instalado.
- **Provider routing:** `integrations/msty/runtime.py`, `aurelius.py` y `aurelius_provider.py` no difieren de main. Las pruebas dirigidas de inyección de endpoints pasan. Un test de Ollama falla en una repetición de la suite completa y pasa por separado: hay indicios de dependencia del estado/orden de pruebas, no una causa demostrada.
- **Cognition states:** se materializan como fases del tribunal y estados de actividad en `ui/flet_app.py` y `ui/war_room_runtime.py`, no como un paquete llamado cognition. El segundo ya coincide con main; el primero contiene mejoras pendientes de refresco y errores. Las pruebas dirigidas de fases pasan.

## Seguridad y política de versionado

Versionar fuentes, tests sintéticos, recursos propios, esquemas, migraciones, prompts, dependencias, scripts, documentación y ejemplos sin credenciales. Excluir `.env` reales, tokens, claves, logs, cachés, bases de datos operativas, embeddings, modelos y memoria personal.

Hallazgo corregido en la rama: `memory/` ignoraba también cinco archivos de código ya seguidos en `core/memory/`, y habría ocultado nuevos módulos. Se sustituyó por `/memory/`. Se añadieron exclusiones para logs/cachés/embeddings raíz, SQLite, modelos GGUF/GGML y ejecutables, junto con exclusiones propias del launcher. Se verificó que el código de memoria queda visible y los ejemplos de datos privados quedan ignorados. No quedan archivos seguidos que coincidan con las reglas de exclusión en esa rama.

El escaneo por patrones de archivos candidatos marcó únicamente placeholders de `.env.example`, accesos a variables/configuración y el detector de secretos del propio código; no se confirmó ninguna credencial. Un segundo control examinó los objetos nuevos respecto a ambas ramas reales de GitHub, sin hallazgos de alta confianza. Los resultados no contienen valores de secretos. Este control no equivale a una garantía exhaustiva ni a una auditoría de todo el historial remoto. Los 714 informes ya publicados siguen recuperables desde commits antiguos aunque se retiren en la rama; no se reescribió historia.

## Validación y límites

- Compilación activa: **497 archivos, PASS**.
- Pruebas dirigidas: **36 passed** (memoria, informes, empaquetado, refresco, routing del launcher, fases y sesiones; incluye Ollama aislado).
- Suite completa, primera ejecución: **666 passed, 12 failed, 1 skipped**.
- Repetición tras copiar los archivos seguidos con sus bytes locales: **665 passed, 13 failed, 1 skipped**. El fallo adicional es el de Ollama citado arriba.
- Comparación con `23749a2` sin cambios pendientes, sobre los módulos visuales/AURELIUS implicados: **35 passed, 4 failed**. Los cuatro son la referencia al bot archivado y tres comprobaciones de hashes de logos; no todos los fallos actuales nacen de los cambios sin commit.
- Los fallos adicionales de GUI afectan anchuras, offsets y márgenes de EVA, WH40K, Military y Helldivers. Debe reconciliarse el diseño esperado con los tests; no se cambiaron aserciones para simular un resultado verde.
- Un test de formato horario falla porque busca `2026-` en toda la salida, que contiene la ruta fechada de esta copia aislada. Es una limitación del test/entorno, no evidencia suficiente de un reloj incorrecto.
- No se reconstruyeron ni ejecutaron los EXE instalados, ni se certificó funcionamiento visual real o comunicación Telegram/móvil. No se cargó el `.env` operativo en la copia de pruebas.

## Commits preparados

| Commit | Alcance |
|---|---|
| `10dfb05` | Recursos y perfiles en el ejecutable |
| `77fc0e2` | Memoria compartida e informes AURELIUS |
| `2e9ba8a` | Refresco GUI, temas, foco y boot |
| `530f8bb` | Fuentes y configuración de ejemplo del launcher |
| `bb95958` | Exclusiones de datos y corrección de `core/memory` |
| `5a1cc11` | Merge de main remoto, sin conflictos |

Se conserva el commit local previo `23749a2` sin reescribirlo. Se añade un commit final de esta auditoría y CHANGELOG. No se cambia el número de versión ni se inventa un tag de release.

## Plan seguro hasta main

1. Publicar exclusivamente la rama de revisión, sin force-push, tras el control de contenido. Verificar el SHA remoto. La publicación respalda fuentes; no declara estabilidad.
2. Revisar por separado la gran retirada de archivos históricos y resolver la prueba del bot archivado según la política de archivo acordada.
3. Revisar los contratos visuales y hashes; aislar caché/entorno en las pruebas de proveedores. Corregir la prueba de fecha para comprobar el campo horario, no rutas de diagnóstico.
4. Ejecutar CI en Linux y validación Windows, reconstrucción del paquete y revisión visual. El workflow actual solo corre en pushes a main y PRs hacia main: publicar una rama sola no ejecuta CI.
5. Abrir un PR de revisión hacia main y fusionar únicamente tras esas validaciones. Crear tag/release solo sobre un commit aprobado, con artefactos comprobados y notas coherentes con la versión elegida.
6. Para actualizar G:, comprobar primero que sus 23 archivos siguen siendo los auditados, guardar sus cambios en commits o en una copia local privada, traer la rama publicada y reconciliarla sin `reset --hard`, sin limpiar archivos ignorados y sin force-push. Después actualizar main local por fast-forward cuando proceda. El árbol operativo no debe sobrescribirse para «limpiar» la auditoría.

El inventario y las salidas de validación acompañan este informe. Los fallos pendientes justifican mantener main y releases sin cambios.
