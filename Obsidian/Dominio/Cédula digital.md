---
tags: [checku, dominio, cedula]
aliases: [cédula de policarbonato, cédula nueva]
---

# Cédula digital

Formato vigente de la cédula de ciudadanía colombiana, expedido por la
Registraduría **desde 2020**. Material: policarbonato.

## Qué trae

**Frente**: foto, NUIP, apellidos, nombres, nacionalidad, estatura, sexo,
fecha y lugar de nacimiento, fecha y lugar de expedición, firma.

**Reverso**: firma del Registrador, **código QR biométrico** y una
**[[MRZ|zona de lectura mecánica de 3 líneas]]**.

Tecnología ABIS para acceso a bases biométricas. Vigencia de 10 años. No
lleva huella impresa (se captura, pero no se imprime).

## Cómo la lee CheckU

Ver [[Pipeline de lectura]]. En resumen:

1. Se busca la [[MRZ]] con una pasada de OCR dedicada a la franja inferior
2. Si aparece → es cédula digital
3. Se parsea con `modules/mrz` (posiciones fijas)
4. Se **cruza** con el texto impreso del frente, porque el MRZ corta los
   nombres a 30 caracteres y se desalinea entero si el OCR pierde un carácter

## Maquetación importante

En este formato la **etiqueta va ARRIBA del valor**:

```
Apellidos          <- etiqueta
MORALES BLANCO     <- valor
Nombres            <- etiqueta
JORGE              <- valor
```

Es al revés que en la [[Cédula amarilla con hologramas]]. Por eso cada
formato tiene su propio módulo de lectura.
