# Guía de Usuario: Sabor - Tu Chef Personal

¡Hola! Soy **Sabor**, tu asistente inteligente de cocina. Estoy aquí para ayudarte a planificar tus comidas, descubrir nuevas recetas y organizar tu vida culinaria sin complicaciones. Esta guía te enseñará todo lo que necesitas saber para empezar.

## 1. Introducción
Sabor es un agente de IA diseñado para simplificar tu alimentación. Aprendo de tus gustos, gestiono tus recetas en Mealie y te ayudo a ahorrar tiempo y dinero mediante una planificación inteligente y automatizada.

## 2. Primeros pasos
Para empezar, solo tienes que saludarme. Lo primero que haré será una pequeña entrevista para conocerte mejor:
- **Tus gustos**: Qué te encanta y qué prefieres evitar.
- **Tus necesidades**: Alergias, intolerancias o dietas específicas (vegetariana, keto, etc.).
- **Tu cocina**: Qué electrodomésticos tienes (horno, air fryer, etc.).

## 3. Flujo semanal
Nuestra rutina suele ser así:
1. **Planificación**: Al final de la semana, diseñamos el menú de la siguiente.
2. **Revisión**: Ajustas cualquier plato que no te apetezca.
3. **Compra**: Genero la lista de ingredientes necesarios.
4. **Cocinado**: Te doy un plan para preparar tus comidas de forma eficiente.

## 4. Comandos/triggers
Puedes interactuar conmigo usando estos comandos específicos. Aquí tienes ejemplos de cómo usarlos:

- **Planifiquemos la semana**
  *Uso:* Pídeme que genere una propuesta de menú.
  *Ejemplo:* "Hola Sabor, **Planifiquemos la semana** por favor."

- **Importa esta receta: [URL]**
  *Uso:* Pásame un enlace de una receta que te guste.
  *Ejemplo:* "**Importa esta receta: https://www.recetas.com/tortilla-de-patata**"

- **Genera la lista de compra**
  *Uso:* Crea una lista organizada con todo lo necesario para tu plan semanal.
  *Ejemplo:* "**Genera la lista de compra** de esta semana."

- **Plan de cocinado**
  *Uso:* Obtén una guía paso a paso para cocinar varios platos a la vez.
  *Ejemplo:* "Voy a empezar ahora, dame el **Plan de cocinado**."

- **Tengo en la nevera: [ingredientes]**
  *Uso:* Dime qué tienes y te sugeriré algo para aprovecharlo.
  *Ejemplo:* "**Tengo en la nevera: calabacín, cebolla y huevos**."

- **El [plato] estaba [rating]**
  *Uso:* Valora las recetas para que pueda aprender de tus gustos (puntuación de 1 a 5).
  *Ejemplo:* "**El risotto de setas estaba 5**."

- **Actualiza mi perfil: [cambio]**
  *Uso:* Informa sobre cambios en tu dieta o preferencias.
  *Ejemplo:* "**Actualiza mi perfil: ahora quiero evitar el gluten**."

## 5. Automatizaciones
Para que no tengas que preocuparte por nada, gestiono varias tareas solo:
- **Recordatorios**: Te aviso cuando es momento de planificar o hacer la compra.
- **Sincronización**: Envío tu lista de compra directamente a tu aplicación de notas preferida.
- **Sugerencias proactivas**: Si detecto que una receta te encantó, te la propondré en el futuro.

## 6. Tips avanzados
- **Sustituciones**: Si te falta un ingrediente, pregúntame por una alternativa.
- **Escalado**: Puedo ajustar las cantidades de las recetas según el número de comensales.
- **Batch Cooking**: Aprovecha el comando de plan de cocinado para dejar lista la comida de varios días en una sola sesión.

## 7. FAQ
1. **¿Dónde se guardan mis recetas?**
Todas tus recetas se almacenan en Mealie, tu gestor personal de recetas al que puedes acceder en cualquier momento.

2. **¿Puedo cambiar un plato del plan semanal una vez confirmado?**
¡Claro! Solo dime qué plato quieres cambiar y te daré alternativas que encajen con tus ingredientes.

3. **¿Cómo sabe Sabor mis alergias?**
Durante nuestra primera conversación (o usando el comando de actualizar perfil), guardo esa información de forma persistente para no sugerirte nunca nada peligroso.

4. **¿La lista de compra incluye cosas de limpieza o higiene?**
Por defecto, me centro en los ingredientes de las recetas planificadas, pero puedes pedirme que añada artículos extra manualmente.

5. **¿Es necesario tener Mealie instalado?**
Sí, yo actúo como la cara visible en Telegram, pero utilizamos Mealie como base de datos para que tus recetas estén siempre organizadas y seguras.

## 8. Arquitectura
Sabor es un ecosistema compuesto por tres partes fundamentales que trabajan en equipo:
- **OpenClaw**: Es el cerebro que gestiona la lógica del agente y la comunicación contigo.
- **Mealie**: Funciona como la base de datos central donde residen tus recetas y planes.
- **Telegram**: Es nuestra interfaz de chat donde ocurre toda la magia.

---
*Última actualización: 2026-02-25*
