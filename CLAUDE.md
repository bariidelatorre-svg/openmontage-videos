# Reglas de trabajo (generación de imágenes con Kie.ai)

- API: Kie.ai con `generar_imagen.py` y la variable `KIE_API_KEY` (nunca mostrar ni commitear su valor).
- Modelo por defecto: **Nano Banana Pro** (`nano-banana-pro`, 2K, 18 créditos/imagen), siempre con las imágenes de `clientes/<clienta>/referencias/` como `image_input`. 4K bloqueado.
- Una imagen por ejecución, sin reintentos automáticos; el script no genera si el saldo no alcanza.
- Cada clienta tiene su carpeta en `clientes/`. Usar sus referencias directamente: **no pedir las imágenes otra vez**.
- **Nunca generar nada desde cero** (sin referencias o con un concepto nuevo) sin consultar antes.
- Formato por defecto: **4:5**. Al entregar una imagen 4:5, preguntar si también se necesita en **9:16**.
- Después de cada generación, informar los **créditos restantes**.
- Si una imagen sale mal, **primero corregirla** con `--corregir <imagen>` (usa la imagen fallida + character sheet + referencias y cambia solo el error); generar una nueva desde la escena solo si la corrección no es posible. La corrección debe tardar lo mismo o menos que una generación nueva: priorizar eficacia y velocidad.
- Si algo falla, intentar arreglarlo primero (parámetros, prompt, código) **sin gastar créditos extra**; no reintentar generaciones a ciegas.
- Respuestas breves y rápidas: mostrar solo el resultado, sin narrar el proceso interno.
- Guardar resultados en `clientes/<clienta>/salidas/`.
- **Identidad absoluta**: en toda imagen de una clienta se mantienen sus rasgos faciales exactos. Pueden variar maquillaje, luz y peinado, nunca los rasgos.
- Al recrear una foto de referencia: respetar luz, cámara/encuadre, contexto, outfit y maquillaje de la referencia, con la identidad de la clienta.
- Entrega doble: guardar cada resultado en `clientes/<clienta>/salidas/` (commit + push) **y** enviarlo en el chat para descargar.
- Nota: Higgsfield se abandonó (`model_disabled` para Nano Banana Pro, oct 2026).
