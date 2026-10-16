# 📸 Photo de référence : Tonton Kofi

Objectif : **une seule** photo photoréaliste, de face, lumière douce et nette. Elle sert de « visage officiel » pour HeyGen et pour toutes les tenues.

## 1. Prompt principal (Midjourney v7, Flux 1.1 Pro, GPT‑Image, Ideogram 3, Leonardo)
```
Ultra-realistic studio portrait photograph of a 42-year-old West African man,
warm deep ebony skin with natural texture and visible pores, oval face, strong square jawline,
short well-groomed salt-and-pepper beard, close-cropped black hair with a subtle low fade
and slightly greying temples, dark brown eyes with a kind, confident and wise gaze,
gentle closed-mouth smile, thin gold-rimmed round glasses, medium solid build.
Wearing a fitted orange and green wax-print shirt, top button open.
Facing the camera directly, head and shoulders framing, shoulders square, centered,
eyes level with the lens. Soft key light at 45 degrees with large softbox, gentle fill,
subtle warm rim light, neutral warm-grey seamless background.
Shot on Canon EOS R5, 85mm f/2.0 lens, sharp focus on the eyes, natural skin tones,
editorial podcast host portrait, photorealistic, 8k, no retouching artifacts.
```

**Paramètres Midjourney :** `--ar 4:5 --style raw --stylize 50 --v 7`
**Flux et Leonardo :** format 1024×1280, guidance de 3 à 3,5, *photorealism* activé.

### Prompt négatif (pour les outils qui l'acceptent)
```
cartoon, 3d render, illustration, plastic skin, airbrushed, overly smooth skin, lightened skin,
distorted glasses, asymmetric eyes, extra fingers, hands in frame, text, watermark, logo,
harsh shadows, side profile, sunglasses, hat, jewelry on face, exaggerated smile, teeth
```

## 2. Choisir la bonne photo
Génère 8 à 12 variantes, puis garde celle qui coche tout :
- [ ] Les deux yeux sont nets, regard droit vers l'objectif, sans reflet gênant dans les lunettes
- [ ] Bouche fermée ou presque (indispensable pour que HeyGen anime bien les lèvres)
- [ ] Aucune main dans l'image, rien devant le visage
- [ ] Peau naturelle, pas « plastique », teint pas éclairci
- [ ] Monture des lunettes symétrique et réaliste
- [ ] Il a vraiment l'air d'avoir 40 à 45 ans : quelques poils gris, mais pas de rides marquées

Agrandis ensuite la photo choisie en 2× (upscale *subtle* dans Midjourney, ou Topaz ou Magnific en mode réaliste) et enregistre-la sous `kofi_reference.png`.

## 3. Créer les 6 tenues sans changer le visage
Avec la photo de référence comme **image de personnage** (Midjourney : `--cref <url> --cw 100`, ou Omni-Reference `--oref <url> --ow 100` ; Flux Kontext ou GPT‑Image : « edit this photo »), donne l'instruction :
```
Same man, same face, same glasses, same beard, same lighting and framing.
Only change his outfit to: <TENUE>
```
| Code | `<TENUE>` |
|---|---|
| T1 | a midnight-blue bazin boubou with fine gold embroidery at the neckline |
| T2 | a fitted orange and green wax-print shirt (photo de référence) |
| T3 | a charcoal-grey tailored suit, crisp white shirt, kente-pattern pocket square |
| T4 | a black polo shirt with a small embroidered orange "E-Maquis" logo on the chest |
| T5 | a white dashiki with subtle embroidery, light linen |
| T6 | a kente-pattern blazer over a plain black crew-neck t-shirt |

Dans **HeyGen** : Avatars → *Photo Avatar* → importer `kofi_reference.png`, puis *Add look* avec chaque image de tenue. Note chaque `avatar_id` dans `pipeline/config.yaml`.

## 4. Le décor (optionnel)
```
Warm cozy podcast studio, wooden table, professional broadcast microphone, soft orange and amber
neon accents, blurred background of an African maquis with colorful plastic chairs and string lights,
shallow depth of field, cinematic, vertical 9:16, photorealistic
```

> ⚖️ Le personnage est fictif. Ne pas utiliser la photo d'une vraie personne sans son accord. Sur YouTube, l'avatar est déclaré comme contenu IA (c'est déjà automatique dans le pipeline).
