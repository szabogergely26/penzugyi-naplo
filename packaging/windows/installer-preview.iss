; ============================================================
; installer-preview.iss — Pénzügyi Napló, PREVIEW (Előzetes) variant
; ============================================================
; Ez a fájl csak a variant-et jelöli ki, a tényleges telepítő
; logika a common.iss-ben van. Ide ne írj [Setup]/[Files]/[Code]
; szekciót — azt a közösbe kell tenni.
; ============================================================

#define AppVariant "preview"
#include "common.iss"
