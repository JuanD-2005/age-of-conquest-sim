# 02 — Informe Técnico Final

**Responsable: María**
**Entregable: `informe_p3.md` en esta carpeta → exportado a PDF para Moodle**
**Vale 30 de los 60 puntos del parcial.**

---

## Qué pide el enunciado, literal

> "Documento académico formal que debe cargarse en formato PDF en Moodle
> antes de la defensa. Debe contener:
> - Descripción general del **alcance del simulador**.
> - **Arquitectura del Software**: Explicación de cómo se estructuró el
>   código (clases, funciones principales, manejo de datos).
> - **Validación y Calibración**: Pueden presentar tablas o gráficas
>   comparativas que demuestren que los resultados arrojados por su
>   simulador coinciden con los resultados del juego real Age of Conquest
>   bajo las mismas condiciones iniciales.
> - **Análisis de Casos Borde**: Explicación de qué ocurre en el simulador
>   ante situaciones extremas (ej. impuestos al máximo, moral en cero,
>   bancarrota)."

---

## El punto clave: este NO es el documento del Parcial II

`docs/parcial2_anexo/age_of_conquest_v4.md` sigue la estructura del rubro del **Parcial II**
(diccionario de variables, ecuaciones, algoritmos, fronteras). El Parcial
III pide otras cuatro secciones. **Casi todo el contenido ya existe**, pero
disperso y con otros títulos.

Este informe es **nuevo y separado**. El `v4.md` pasa a ser **anexo técnico**
— se referencia, no se copia entero.

---

## Mapa: de dónde sacar cada sección

| Sección que pide P3 | Material que ya existe | Qué hay que hacer |
|---|---|---|
| **Alcance del simulador** | No existe como tal | Escribir desde cero. Qué SÍ hace el motor (5 eventos, 3 políticas de IA, economía, combate estocástico) y qué NO (sin interfaz gráfica, sin mapas del juego comercial — el enunciado dice explícitamente que eso no se requiere) |
| **Arquitectura del Software** | §7 del `v4.md` (tabla de módulos) + `README.md` (grafo de dependencias) | Expandir a prosa: cómo se comunican los módulos, qué clases hay (`Partida`, `Imperio`, `Provincia`, `OrdenMilitar`, `Mapa`, `LEF`), cómo fluyen los datos por la LEF |
| **Validación y Calibración** | §6.5 (validación del generador), §7.1 (31 verificaciones), `sensibilidad.py`, `replicas.py` | **Coordinar con Gustavo** — él está armando la estrategia de esta sección, que tiene un matiz delicado (ver abajo) |
| **Análisis de Casos Borde** | §4 del `v4.md` (F1–F10) — ya está completísimo | Reescribir en el formato que pide P3. Ojo: el enunciado da ejemplos concretos ("impuestos al máximo, moral en cero, bancarrota") que conviene abordar uno por uno |

---

## Dos avisos importantes

### 1. Sobre "moral en cero"
El enunciado menciona *"moral en cero"* como ejemplo de caso borde. **En
nuestro modelo la moral no existe** — está justificado en la "Nota de
coherencia" de §1.4 del `v4.md`: el Parcial I la mencionaba como ejemplo
genérico, pero no era un atributo de ninguna entidad formalizada, y su rol
funcional lo cumplen `estadoFinanciero = BANCARROTA` y
`tropasEstacionadas = 0`.

**No la inventes ahora** para que calce con el enunciado. Explica en el
informe por qué no existe y qué la sustituye. Es una decisión de diseño
defendible y documentada desde el Parcial II — improvisar una variable
"moral" a última hora rompería la coherencia de todo el modelo.

### 2. Sobre "impuestos al máximo"
Ese caso borde **no está en F1–F10**. Cuando Juan tenga `main.py` con la
tasa impositiva ajustable, vale la pena probarlo y documentar qué pasa.
Coordina con él.

---

## Formato

- Escribir en Markdown (`informe_p3.md`) y exportar a PDF al final.
- **Importante sobre el PDF:** el `v4.pdf` se generó con una herramienta
  que renderiza LaTeX y Mermaid correctamente. GitHub NO los renderiza.
  Pregúntale a Juan qué método usó antes de exportar, para no perder las
  ecuaciones.
- Se puede reutilizar texto del `v4.md` citándolo como anexo, pero el
  informe debe leerse solo: un evaluador no debería tener que abrir el
  anexo para entender el alcance o la arquitectura.

---

## Para la defensa

Vas a defender este informe. Prepárate para:
- Explicar la arquitectura sin mirar el código
- Justificar por qué no hay "moral" en el modelo
- Explicar qué es la LEF y por qué el orden de desempate importa
