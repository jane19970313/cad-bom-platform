"use client";

import {
  useCallback,
  useRef,
  useState,
  type MutableRefObject,
} from "react";

import { AcCmColor } from "@mlightcad/common";

interface MaterialSnapshot {
  material: any;
  color: any;
}

export function useCadMonochrome(
  managerRef: MutableRefObject<any>
) {
  const [monochrome, setMonochrome] = useState(false);

  const originalLayerColorsRef =
    useRef<Map<string, AcCmColor> | null>(null);

  const originalMaterialColorsRef =
    useRef<Map<string, MaterialSnapshot> | null>(null);

  const originalShaderColorsRef =
    useRef<Map<string, any> | null>(null);

  const toggleMonochrome = useCallback(() => {
    const manager = managerRef.current;
    const view = manager?.curView;
    const database = manager?.curDocument?.database;

    if (!view || !database) return;

    const layerTable = database._tables.layerTable;

    if (!monochrome) {
      // Save and override layer colors.
      const layerColors = new Map<string, AcCmColor>();

      for (const layer of layerTable.newIterator()) {
        layerColors.set(layer.name, layer.color);

        layer.color = new AcCmColor().setRGB(
          170,
          170,
          170
        );

        view.updateLayer(layer, {
          color: layer.color,
        });
      }

      originalLayerColorsRef.current = layerColors;

      // Save and override regular material colors.
      const materialColors =
        new Map<string, MaterialSnapshot>();

      view.internalScene.children.forEach((root: any) => {
        root.traverse((object: any) => {
          if (!object.material) return;

          const materials = Array.isArray(object.material)
            ? object.material
            : [object.material];

          for (const material of materials) {
            if (
              !material.color ||
              materialColors.has(material.uuid)
            ) {
              continue;
            }

            materialColors.set(material.uuid, {
              material,
              color: material.color.clone(),
            });

            material.color.setRGB(0.67, 0.67, 0.67);
            material.needsUpdate = true;
          }
        });
      });

      originalMaterialColorsRef.current = materialColors;

      // Save and override custom shader colors.
      const shaderColors = new Map<string, any>();

      view.internalScene.traverse((layerGroup: any) => {
        if (!layerGroup.name) return;

        layerGroup.traverse((child: any) => {
          if (!child.material) return;

          const materials = Array.isArray(child.material)
            ? child.material
            : [child.material];

          materials.forEach((material: any) => {
            const color = material.uniforms?.u_color?.value;

            if (!color?.clone) return;

            if (!shaderColors.has(layerGroup.name)) {
              shaderColors.set(
                layerGroup.name,
                color.clone()
              );
            }

            color.setRGB(0.67, 0.67, 0.67);
          });
        });
      });

      originalShaderColorsRef.current = shaderColors;
      setMonochrome(true);
      return;
    }

    // Restore layer colors.
    const originalLayers = originalLayerColorsRef.current;

    if (originalLayers) {
      for (const layer of layerTable.newIterator()) {
        const original = originalLayers.get(layer.name);

        if (!original) continue;

        layer.color = original;

        view.updateLayer(layer, {
          color: original,
        });
      }
    }

    // Restore material colors.
    originalMaterialColorsRef.current?.forEach(
      ({ material, color }) => {
        material.color.copy(color);
        material.needsUpdate = true;
      }
    );

    // Restore custom shader colors.
    view.internalScene.traverse((layerGroup: any) => {
      if (!layerGroup.name) return;

      const original =
        originalShaderColorsRef.current?.get(layerGroup.name);

      if (!original) return;

      layerGroup.traverse((child: any) => {
        if (!child.material) return;

        const materials = Array.isArray(child.material)
          ? child.material
          : [child.material];

        materials.forEach((material: any) => {
          const color = material.uniforms?.u_color?.value;

          if (color?.copy) {
            color.copy(original);
          }
        });
      });
    });

    originalLayerColorsRef.current = null;
    originalMaterialColorsRef.current = null;
    originalShaderColorsRef.current = null;

    setMonochrome(false);
  }, [managerRef, monochrome]);

  return {
    monochrome,
    toggleMonochrome,
  };
}