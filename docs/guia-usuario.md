# Guía de Usuario: Sabor - Tu Chef Personal en Telegram

¡Hola! Soy **Sabor**, tu asistente inteligente de cocina. Esta guía explica todo lo que puedes hacer conmigo y cómo saco partido de Mealie para organizarte la vida culinaria.

---

## 1. Primeros pasos — Onboarding

La primera vez que me escribas, te haré una entrevista breve con **botones** para conocerte:

- Cuántas personas coméis en casa
- Presupuesto semanal
- Alergias o restricciones alimentarias
- Electrodomésticos disponibles (horno, air fryer, Thermomix, etc.)
- Cocinas favoritas y platos que no te gustan
- **Modelo de planificación preferido** (ver sección 2)

Con esto creo tu perfil. Puedes actualizarlo en cualquier momento.

---

## 2. Cómo funciona el menú semanal

Planifico **de lunes a viernes** (comida + cena). Nunca sábado ni domingo — el finde lo gestionas tú.

Hay **3 modelos de planificación** que adaptan las porciones para que no te sobre nada:

### 🔄 Escalonado — Variedad diaria, 0 desperdicio
Cocinas cada noche en 25-35 min. La cena de hoy es tu comida de mañana.
- **5 recetas** × 2 porciones c/u
- **5 sesiones** de cocina (una por tarde)
- Lunes comida: libre / tupper semana anterior
- Viernes cena → tupper del finde

### 🗓️ Emparejado — Solo 3 días de cocina
Cocinas lunes, miércoles y viernes. Cada receta cubre 2 días.
- **6 recetas** × 2 porciones c/u
- **3 sesiones** (L, X, V)
- Martes y jueves: recalientas lo de ayer

### 🔥 Batch — Una sesión larga el domingo
Cocinas todo el domingo (~2h) y el resto de la semana solo recalientas.
- **4 recetas** (3×4 porciones + 1×2 porciones para el viernes)
- **1 sesión** de batch (~2h domingo) + cocina fresca el viernes

---

## 3. Flujo semanal típico

```
Domingo tarde
  → "Planifiquemos la semana"
  → Elige o aprueba el menú con botones
  → ✅ Confirmar → Sabor actualiza el calendario de Mealie
                 → Genera la lista de compra en Mealie
                 → Prepara el plan de cocinado

Lunes (o domingo si haces batch)
  → "Dame el plan de cocinado"
  → Sigues el plan
  → "He terminado el batch" → Sabor registra lo cocinado en Mealie

Durante la semana
  → "El pad thai de anoche estaba un 5 ⭐" → Sabor guarda el feedback
  → Lo ve reflejado en la receta de Mealie como comentario

Fin de semana
  → Abres Mealie en el ordenador y ves el calendario con los platos de la semana
```

---

## 4. Comandos y frases naturales

No hay comandos estrictos — escríbeme como hablarías a un chef amigo. Estos son los más frecuentes:

### Planificación
| Frase | Resultado |
|---|---|
| `Planifiquemos la semana` | Genera el menú L-V con tu modelo preferido |
| `Cambia la cena del miércoles` | Selector de alternativas con botones |
| `Regenera el menú completo` | Nuevo menú respetando tus preferencias |
| `Quiero cambiar al modo batch esta semana` | Cambia el modelo y regenera |

### Recetas
| Frase | Resultado |
|---|---|
| `Importa esta receta: [URL]` | Importa a Mealie y auto-etiqueta (cocina, tiempo, método) |
| `Busca recetas de pollo` | Busca en Mealie, luego en Spoonacular si no hay |
| `Crea una receta de ensalada césar` | Abre el asistente de creación manual |

### Lista de compra
| Frase | Resultado |
|---|---|
| `Genera la lista de la compra` | Crea la lista en Mealie con todos los ingredientes del menú |
| `Tengo en la nevera: zanahoria, cebolla` | Vaciado inteligente de nevera |

### Feedback
| Frase | Resultado |
|---|---|
| `El risotto estaba un 5` | Guarda ⭐⭐⭐⭐⭐ en tu perfil y en Mealie |
| `El curry no me gustó, nunca más` | Añade a blacklist — no volverá a aparecer |
| `Esa receta es una favorita` | Priorizada en futuros menús |

### Cocinado
| Frase | Resultado |
|---|---|
| `Dame el plan de cocinado` | Plan de batch con orden y tiempos |
| `He terminado de cocinar` | Registra el historial en el timeline de Mealie |
| `¿Cuánto tiempo me lleva el batch de hoy?` | Estimación detallada |

---

## 5. El panel de Mealie en tu ordenador

Cada vez que confirmas el menú semanal, Sabor actualiza automáticamente en Mealie:

- **📅 Calendario**: cada comida y cena de L-V aparece en el calendario visual, con enlace a la receta si existe en tu biblioteca
- **🛒 Lista de compra**: todos los ingredientes necesarios para la semana
- **🏷️ Tags**: las recetas importadas se etiquetan automáticamente (ej: `japonesa`, `rápido`, `air-fryer`, `batch-friendly`)
- **💬 Comentarios**: cuando das feedback, aparece como comentario en la receta
- **📋 Timeline**: cuando terminas de cocinar, queda registrado el historial de cada receta

### Acceder al panel

**Opción A — Túnel SSH:**
```bash
ssh -L 9925:localhost:9925 root@<IP_VPS> -N
```
Luego abre `http://localhost:9925` en el navegador.

**Opción B — Tailscale (recomendado):**
Instala [Tailscale](https://tailscale.com/download), inicia sesión con la misma cuenta que la VPS y accede a `http://100.82.166.82:9925` directamente.

---

## 6. Tu perfil — qué guarda Sabor

Todo lo que aprendo de ti se guarda en MEMORY.md y evoluciona con el tiempo:

- **Perfil básico**: comensales, presupuesto, equipamiento
- **Restricciones**: alergias, blacklist de ingredientes y recetas
- **Preferencias aprendidas**: tipos de cocina favoritos, feedback histórico
- **Modelo de planificación**: Escalonado / Emparejado / Batch
- **Historial de menús**: las últimas semanas para no repetir platos

Puedes pedirme que te lo muestre o actualices en cualquier momento: *"¿Cómo tienes guardado mi perfil?"*

---

## 7. Preguntas frecuentes

**¿Puedo cambiar el modelo de planificación?**
Sí, en cualquier momento: *"Quiero cambiar al modelo batch"* o pulsando el botón correspondiente al generar el menú.

**¿Qué pasa si una receta no está en Mealie?**
Sabor la añade igualmente al calendario de texto. Puedes importarla después: *"Importa esta receta: [URL]"*.

**¿Puedo planificar solo algunos días?**
Sí: *"Solo necesito planificar miércoles, jueves y viernes"*.

**¿Puedo ver el menú de la semana sin abrir Mealie?**
Claro: *"¿Qué tengo planificado esta semana?"* y te lo muestro en Telegram.

**¿Se sincronizan los cambios si edito algo en Mealie directamente?**
Mealie es la fuente de verdad para recetas y calendarios. Si editas en Mealie, Sabor lo verá en la próxima consulta. Si editas en Telegram, Sabor actualiza Mealie automáticamente.
