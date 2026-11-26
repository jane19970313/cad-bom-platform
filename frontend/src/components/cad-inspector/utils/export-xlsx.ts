
import ExcelJS from "exceljs";
import type { BomElement } from "@/src/types/analysis";

/* =========================================================
   SteelMind AI — Professional BOM Excel Generator
   Five-sheet manufacturing workbook
   ========================================================= */

/* -------------------- Design system -------------------- */

const C = {
  navy: "142B4A",
  deep: "0B1D33",
  blue: "1E5B91",
  cyan: "16B8C8",
  cyanLight: "DDF6F7",
  blueLight: "DCEAF6",
  green: "16866A",
  greenLight: "E3F4EE",
  amber: "B7791F",
  amberLight: "FFF4D9",
  red: "C0392B",
  redLight: "FCE8E6",
  ink: "24364B",
  muted: "6B7C90",
  border: "D7E1EB",
  white: "FFFFFF",
  canvas: "F3F7FB",
  alternate: "F4F8FC",
};

const FONT = "Microsoft YaHei";
const NUM = '#,##0.00;[Red]-#,##0.00;"—"';
const INT = '#,##0;[Red]-#,##0;"—"';
const PCT = "0.0%";

const SHEET = {
  overview: "项目总览",
  detail: "钢格板BOM明细",
  material: "材料汇总",
  specification: "规格汇总",
  guide: "字段说明",
};

const FIRST_DATA_ROW = 6;

type NormalizedRow = {
  index: number;
  caption: string;
  length: number | null;
  material: string;
  area: number | null;
  count: number;
  volume: number | null;
  mass: number | null;
  totalArea: number;
  totalMass: number;
  handles: string;
};

type MaterialGroup = {
  material: string;
  lineCount: number;
  quantity: number;
  area: number;
  mass: number;
};

type SpecificationGroup = {
  caption: string;
  length: number | null;
  material: string;
  lineCount: number;
  quantity: number;
  area: number;
  mass: number;
};

/* -------------------- Utilities -------------------- */

function sum(values: number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const result = Number(value);

  return Number.isFinite(result) ? result : null;
}

function toNonNegativeNumber(value: unknown): number | null {
  const result = toNumber(value);

  return result !== null && result >= 0 ? result : null;
}

function toText(value: unknown, fallback = "未指定"): string {
  if (value === null || value === undefined) {
    return fallback;
  }

  const result = String(value).trim();

  return result || fallback;
}

function excelFormula(
  formula: string,
  result: number | string
): ExcelJS.CellFormulaValue {
  return {
    formula,
    result,
  };
}

function normalizeData(elements: BomElement[]): NormalizedRow[] {
  return elements.map((element, index) => {
    const countValue = toNonNegativeNumber(element.count);

    const count = countValue ?? 0;
    const area = toNonNegativeNumber(element.area);
    const mass = toNonNegativeNumber(element.mass);
    const length = toNonNegativeNumber(element.length);
    const volume = toNonNegativeNumber(element.volume);

    return {
      index: index + 1,
      caption: toText(element.caption, "未命名构件"),
      length,
      material: toText(element.material),
      area,
      count,
      volume,
      mass,
      totalArea: (area ?? 0) * count,
      totalMass: (mass ?? 0) * count,
      handles: Array.isArray(element.source_handles)
        ? element.source_handles.map(String).join(", ")
        : "",
    };
  });
}

/* -------------------- Grouping -------------------- */

function groupMaterials(rows: NormalizedRow[]): MaterialGroup[] {
  const groups = new Map<string, MaterialGroup>();

  for (const item of rows) {
    const group = groups.get(item.material) ?? {
      material: item.material,
      lineCount: 0,
      quantity: 0,
      area: 0,
      mass: 0,
    };

    group.lineCount += 1;
    group.quantity += item.count;
    group.area += item.totalArea;
    group.mass += item.totalMass;

    groups.set(item.material, group);
  }

  return [...groups.values()].sort((a, b) => b.mass - a.mass);
}

function groupSpecifications(
  rows: NormalizedRow[]
): SpecificationGroup[] {
  const groups = new Map<string, SpecificationGroup>();

  for (const item of rows) {
    const key = JSON.stringify([
      item.caption,
      item.length,
      item.material,
    ]);

    const group = groups.get(key) ?? {
      caption: item.caption,
      length: item.length,
      material: item.material,
      lineCount: 0,
      quantity: 0,
      area: 0,
      mass: 0,
    };

    group.lineCount += 1;
    group.quantity += item.count;
    group.area += item.totalArea;
    group.mass += item.totalMass;

    groups.set(key, group);
  }

  return [...groups.values()].sort(
    (a, b) =>
      b.mass - a.mass ||
      a.caption.localeCompare(b.caption, "zh-CN")
  );
}

/* -------------------- Common worksheet styling -------------------- */

function setupSheet(
  ws: ExcelJS.Worksheet,
  tabColor: string
): void {
  ws.properties.tabColor = {
    argb: `FF${tabColor.replace("#", "").toUpperCase()}`,
  };

  ws.properties.defaultRowHeight = 22;

  ws.views = [{
    showGridLines: false,
  }];

  ws.pageSetup = {
    paperSize: 9,
    orientation: "landscape",
    fitToPage: true,
    fitToWidth: 1,
    fitToHeight: 0,
    margins: {
      left: 0.25,
      right: 0.25,
      top: 0.5,
      bottom: 0.5,
      header: 0.2,
      footer: 0.2,
    },
  };

  ws.headerFooter.oddFooter =
    "&LSteelMind AI  |  智能钢格板 BOM" +
    "&C第 &P 页 / 共 &N 页" +
    "&R内部制造资料";
}

function setTitle(
  ws: ExcelJS.Worksheet,
  title: string,
  subtitle: string,
  columns: number
): void {
  ws.mergeCells(1, 1, 2, columns);

  const titleCell = ws.getCell(1, 1);

  titleCell.value = title;
  titleCell.font = {
    name: FONT,
    size: 21,
    bold: true,
    color: { argb: C.white },
  };

  titleCell.alignment = {
    vertical: "middle",
    horizontal: "left",
    indent: 1,
  };

  titleCell.fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: C.navy },
  };

  ws.getRow(1).height = 30;
  ws.getRow(2).height = 23;

  ws.mergeCells(3, 1, 3, columns);

  const subtitleCell = ws.getCell(3, 1);

  subtitleCell.value = subtitle;
  subtitleCell.font = {
    name: FONT,
    size: 9,
    color: { argb: C.muted },
    italic: true,
  };

  subtitleCell.alignment = {
    vertical: "middle",
    horizontal: "left",
    indent: 1,
  };

  subtitleCell.fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: C.canvas },
  };

  ws.getRow(3).height = 24;
}

function styleHeader(row: ExcelJS.Row): void {
  row.height = 32;

  row.eachCell((cell) => {
    cell.font = {
      name: FONT,
      size: 10,
      bold: true,
      color: { argb: C.white },
    };

    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: C.blue },
    };

    cell.alignment = {
      vertical: "middle",
      horizontal: "center",
      wrapText: true,
    };

    cell.border = {
      top: {
        style: "thin",
        color: { argb: C.blue },
      },
      bottom: {
        style: "medium",
        color: { argb: C.cyan },
      },
      left: {
        style: "thin",
        color: { argb: "4F7FA8" },
      },
      right: {
        style: "thin",
        color: { argb: "4F7FA8" },
      },
    };
  });
}

function styleBody(
  ws: ExcelJS.Worksheet,
  start: number,
  end: number,
  columns: number
): void {
  for (let r = start; r <= end; r++) {
    const row = ws.getRow(r);

    row.height = 25;

    for (let col = 1; col <= columns; col++) {
      const cell = row.getCell(col);

      cell.font = {
        name: FONT,
        size: 9,
        color: { argb: C.ink },
      };

      cell.fill = {
        type: "pattern",
        pattern: "solid",
        fgColor: {
          argb: r % 2 === 0 ? C.white : C.alternate,
        },
      };

      cell.alignment = {
        vertical: "middle",
        wrapText: true,
      };

      cell.border = {
        bottom: {
          style: "hair",
          color: { argb: C.border },
        },
      };
    }
  }
}

function styleTotal(row: ExcelJS.Row, columns: number): void {
  row.height = 31;

  for (let col = 1; col <= columns; col++) {
    const cell = row.getCell(col);

    cell.font = {
      name: FONT,
      size: 10,
      bold: true,
      color: { argb: C.navy },
    };

    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: C.cyanLight },
    };

    cell.border = {
      top: {
        style: "medium",
        color: { argb: C.cyan },
      },
      bottom: {
        style: "thin",
        color: { argb: C.border },
      },
    };

    cell.alignment = {
      vertical: "middle",
      horizontal: "right",
    };
  }

  row.getCell(1).alignment = {
    vertical: "middle",
    horizontal: "left",
  };
}

function section(
  ws: ExcelJS.Worksheet,
  row: number,
  firstCol: number,
  lastCol: number,
  label: string
): void {
  ws.mergeCells(row, firstCol, row, lastCol);

  const cell = ws.getCell(row, firstCol);

  cell.value = label;
  cell.font = {
    name: FONT,
    size: 11,
    bold: true,
    color: { argb: C.navy },
  };

  cell.fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: C.blueLight },
  };

  cell.alignment = {
    vertical: "middle",
    horizontal: "left",
    indent: 1,
  };

  cell.border = {
    bottom: {
      style: "medium",
      color: { argb: C.cyan },
    },
  };

  ws.getRow(row).height = 28;
}

function setCell(
  ws: ExcelJS.Worksheet,
  address: string,
  value: ExcelJS.CellValue
): void {
  ws.getCell(address).value = value;
}

function setNumberFormat(
  ws: ExcelJS.Worksheet,
  row: number,
  columns: number[],
  format = NUM
): void {
  for (const col of columns) {
    ws.getRow(row).getCell(col).numFmt = format;
  }
}

function addEmptyState(
  ws: ExcelJS.Worksheet,
  row: number,
  columns: number,
  message: string
): void {
  ws.mergeCells(row, 1, row, columns);

  const cell = ws.getCell(row, 1);

  cell.value = message;
  cell.font = {
    name: FONT,
    size: 10,
    color: { argb: C.muted },
    italic: true,
  };

  cell.alignment = {
    horizontal: "center",
    vertical: "middle",
  };

  cell.fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: C.canvas },
  };

  ws.getRow(row).height = 38;
}

/* -------------------- KPI cards -------------------- */

function addKpi(
  ws: ExcelJS.Worksheet,
  firstCol: number,
  lastCol: number,
  label: string,
  formula: string,
  result: number,
  unit: string,
  accent: string,
  format = NUM
): void {
  ws.mergeCells(5, firstCol, 5, lastCol);
  ws.mergeCells(6, firstCol, 7, lastCol);
  ws.mergeCells(8, firstCol, 8, lastCol);

  const labelCell = ws.getCell(5, firstCol);

  labelCell.value = label;
  labelCell.font = {
    name: FONT,
    size: 10,
    bold: true,
    color: { argb: C.muted },
  };

  labelCell.alignment = {
    vertical: "middle",
    horizontal: "center",
  };

  const valueCell = ws.getCell(6, firstCol);

  valueCell.value = excelFormula(formula, result);
  valueCell.numFmt = format;
  valueCell.font = {
    name: FONT,
    size: 22,
    bold: true,
    color: { argb: accent },
  };

  valueCell.alignment = {
    vertical: "middle",
    horizontal: "center",
  };

  const unitCell = ws.getCell(8, firstCol);

  unitCell.value = unit;
  unitCell.font = {
    name: FONT,
    size: 9,
    color: { argb: C.muted },
  };

  unitCell.alignment = {
    vertical: "middle",
    horizontal: "center",
  };

  for (let r = 5; r <= 8; r++) {
    for (let col = firstCol; col <= lastCol; col++) {
      const cell = ws.getCell(r, col);

      cell.fill = {
        type: "pattern",
        pattern: "solid",
        fgColor: { argb: C.white },
      };

      cell.border = {
        top: {
          style: "medium",
          color: { argb: accent },
        },
        bottom: {
          style: "thin",
          color: { argb: C.border },
        },
        left: {
          style: "thin",
          color: { argb: C.border },
        },
        right: {
          style: "thin",
          color: { argb: C.border },
        },
      };
    }
  }
}

/* =========================================================
   SHEET 1 — Project Overview Dashboard
   ========================================================= */

function createOverview(
  workbook: ExcelJS.Workbook,
  rows: NormalizedRow[],
  materials: MaterialGroup[],
  specs: SpecificationGroup[]
): void {
  const ws = workbook.addWorksheet(SHEET.overview);

  setupSheet(ws, C.cyan);

  ws.columns = [
    { width: 19 },
    { width: 15 },
    { width: 15 },
    { width: 17 },
    { width: 17 },
    { width: 16 },
    { width: 16 },
    { width: 16 },
  ];

  setTitle(
    ws,
    "STEELMIND AI  |  钢格板制造 BOM",
    "CAD 智能解析结果 · 自动生成的制造物料清单与统计报告",
    8
  );

  const detailLastRow = FIRST_DATA_ROW + rows.length - 1;
  const detailSheet = `'${SHEET.detail}'`;

  const totalQty = sum(rows.map(x => x.count));
  const totalArea = sum(rows.map(x => x.totalArea));
  const totalMass = sum(rows.map(x => x.totalMass));

  addKpi(
    ws,
    1,
    2,
    "BOM 构件总数",
    `SUM(${detailSheet}!$F$${FIRST_DATA_ROW}:$F$${detailLastRow})`,
    totalQty,
    "件 · 按数量字段统计",
    C.blue,
    INT
  );

  addKpi(
    ws,
    4,
    5,
    "理论总面积",
    `SUM(${detailSheet}!$G$${FIRST_DATA_ROW}:$G$${detailLastRow})`,
    totalArea,
    "m² · 单件面积 × 数量",
    C.cyan
  );

  addKpi(
    ws,
    7,
    8,
    "理论总重量",
    `SUM(${detailSheet}!$J$${FIRST_DATA_ROW}:$J$${detailLastRow})`,
    totalMass,
    "kg · 单件重量 × 数量",
    C.green
  );

  section(ws, 10, 1, 4, "项目数据概况");
  section(ws, 10, 5, 8, "数据完整性检查");

  const overview: [string, string | number][] = [
    ["BOM 明细行数", rows.length],
    ["材料类别数", materials.length],
    ["规格类别数", specs.length],
    [
      "导出时间",
      new Date().toLocaleString("zh-CN", {
        hour12: false,
      }),
    ],
  ];

  overview.forEach(([label, value], index) => {
    const r = 11 + index;

    ws.mergeCells(r, 1, r, 2);
    ws.mergeCells(r, 3, r, 4);

    ws.getCell(r, 1).value = label;
    ws.getCell(r, 3).value = value;

    ws.getCell(r, 1).font = {
      name: FONT,
      size: 9,
      color: { argb: C.muted },
    };

    ws.getCell(r, 3).font = {
      name: FONT,
      size: 9,
      bold: true,
      color: { argb: C.ink },
    };

    ws.getCell(r, 1).fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: C.canvas },
    };

    ws.getCell(r, 3).fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: C.white },
    };

    ws.getCell(r, 1).alignment = {
      vertical: "middle",
      indent: 1,
    };

    ws.getCell(r, 3).alignment = {
      vertical: "middle",
      indent: 1,
    };

    for (let col = 1; col <= 4; col++) {
      ws.getCell(r, col).border = {
        bottom: {
          style: "thin",
          color: { argb: C.border },
        },
      };
    }
  });

  const quality = [
    [
      "未填写材质",
      rows.filter(x => x.material === "未指定").length,
    ],
    [
      "未填写单件面积",
      rows.filter(x => x.area === null).length,
    ],
    [
      "未填写单件重量",
      rows.filter(x => x.mass === null).length,
    ],
    [
      "未填写长度",
      rows.filter(x => x.length === null).length,
    ],
  ];

  quality.forEach(([label, value], index) => {
    const r = 11 + index;

    ws.mergeCells(r, 5, r, 7);

    ws.getCell(r, 5).value = label;
    ws.getCell(r, 8).value = value;

    ws.getCell(r, 5).font = {
      name: FONT,
      size: 9,
      color: { argb: C.muted },
    };

    ws.getCell(r, 8).font = {
      name: FONT,
      size: 10,
      bold: true,
      color: Number(value) > 0 ? { argb: C.amber } : { argb: C.green },
    };

    ws.getCell(r, 5).fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: C.canvas },
    };

    ws.getCell(r, 8).fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: Number(value) > 0
        ? { argb: C.amberLight }
        : { argb: C.greenLight },
    };

    ws.getCell(r, 5).alignment = {
      vertical: "middle",
      indent: 1,
    };

    ws.getCell(r, 8).alignment = {
      vertical: "middle",
      horizontal: "center",
    };

    for (let col = 5; col <= 8; col++) {
      ws.getCell(r, col).border = {
        bottom: {
          style: "thin",
          color: { argb: C.border },
        },
      };
    }
  });

  section(ws, 17, 1, 8, "材料重量分布");

  const header = ws.getRow(18);

  header.values = [
    "材质",
    "明细行数",
    "总数量",
    "总面积 (m²)",
    "总重量 (kg)",
    "重量占比",
    "",
    "",
  ];

  ws.mergeCells("F18:G18");
  styleHeader(header);

  const topMaterials = materials.slice(0, 8);

  if (topMaterials.length === 0) {
    addEmptyState(ws, 19, 8, "暂无材料汇总数据");
  }

  topMaterials.forEach((item, index) => {
    const r = 19 + index;
    const materialRow = 6 + materials.findIndex(
      x => x.material === item.material
    );

    const formulaPrefix = `'${SHEET.material}'`;

    ws.getCell(r, 1).value = item.material;

    ws.getCell(r, 2).value = excelFormula(
      `${formulaPrefix}!B${materialRow}`,
      item.lineCount
    );

    ws.getCell(r, 3).value = excelFormula(
      `${formulaPrefix}!C${materialRow}`,
      item.quantity
    );

    ws.getCell(r, 4).value = excelFormula(
      `${formulaPrefix}!D${materialRow}`,
      item.area
    );

    ws.getCell(r, 5).value = excelFormula(
      `${formulaPrefix}!E${materialRow}`,
      item.mass
    );

    ws.getCell(r, 6).value = excelFormula(
      `${formulaPrefix}!F${materialRow}`,
      totalMass > 0 ? item.mass / totalMass : 0
    );

    ws.mergeCells(r, 6, r, 7);

    setNumberFormat(ws, r, [2, 3], INT);
    setNumberFormat(ws, r, [4, 5], NUM);
    setNumberFormat(ws, r, [6], PCT);

    for (let col = 1; col <= 7; col++) {
      const cell = ws.getCell(r, col);

      cell.font = {
        name: FONT,
        size: 9,
        color: { argb: C.ink },
      };

      cell.fill = {
        type: "pattern",
        pattern: "solid",
        fgColor: {
          argb: r % 2 ? C.alternate : C.white,
        },
      };

      cell.alignment = {
        vertical: "middle",
        horizontal: col === 1 ? "left" : "right",
      };

      cell.border = {
        bottom: {
          style: "hair",
          color: { argb: C.border },
        },
      };
    }
  });

  const noteRow = Math.max(21, 20 + topMaterials.length);

  ws.mergeCells(noteRow, 1, noteRow + 1, 8);

  const note = ws.getCell(noteRow, 1);

  note.value =
    "统计口径：总面积 = 单件面积 × 数量；总重量 = 单件重量 × 数量。缺失数值按 0 参与统计，并在数据完整性检查中提示。材料汇总及 BOM 数量使用 Excel 公式。正式采购和生产前请复核图纸及工艺要求。";

  note.font = {
    name: FONT,
    size: 9,
    color: { argb: C.muted },
    italic: true,
  };

  note.alignment = {
    vertical: "middle",
    horizontal: "left",
    wrapText: true,
    indent: 1,
  };

  note.fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: C.canvas },
  };

  note.border = {
    left: {
      style: "medium",
      color: { argb: C.cyan },
    },
  };

  ws.getRow(noteRow).height = 32;
  ws.getRow(noteRow + 1).height = 22;

  ws.views = [{
    state: "frozen",
    ySplit: 3,
    topLeftCell: "A4",
    showGridLines: false,
  }];

  ws.pageSetup.printArea = `A1:H${noteRow + 1}`;
}

/* =========================================================
   SHEET 2 — Detailed BOM
   ========================================================= */

function createBomDetail(
  workbook: ExcelJS.Workbook,
  rows: NormalizedRow[]
): void {
  const ws = workbook.addWorksheet(SHEET.detail);

  setupSheet(ws, C.blue);

  ws.columns = [
    { width: 8 },
    { width: 27 },
    { width: 14 },
    { width: 17 },
    { width: 15 },
    { width: 10 },
    { width: 16 },
    { width: 15 },
    { width: 15 },
    { width: 16 },
    { width: 34 },
  ];

  setTitle(
    ws,
    "钢格板 BOM 明细清单",
    "逐项列出 CAD 识别构件、规格参数、数量及材料用量",
    11
  );

  const headerRow = 5;
  const header = ws.getRow(headerRow);

  header.values = [
    "序号",
    "构件名称",
    "长度 (mm)",
    "材质",
    "单件面积 (m²)",
    "数量",
    "合计面积 (m²)",
    "单件体积 (m³)",
    "单件重量 (kg)",
    "合计重量 (kg)",
    "CAD 实体句柄",
  ];

  styleHeader(header);

  rows.forEach((item, index) => {
    const r = FIRST_DATA_ROW + index;
    const row = ws.getRow(r);

    row.values = [
      item.index,
      item.caption,
      item.length,
      item.material,
      item.area,
      item.count,
      excelFormula(`E${r}*F${r}`, item.totalArea),
      item.volume,
      item.mass,
      excelFormula(`I${r}*F${r}`, item.totalMass),
      item.handles,
    ];

    row.getCell(1).alignment = {
      horizontal: "center",
      vertical: "middle",
    };

    [3, 5, 7, 8, 9, 10].forEach(col => {
      row.getCell(col).numFmt = NUM;
    });

    row.getCell(6).numFmt = INT;
  });

  const lastDataRow = FIRST_DATA_ROW + rows.length - 1;
  const totalRowNumber = lastDataRow + 1;

  const total = ws.getRow(totalRowNumber);

  total.getCell(1).value = "合计";
  total.getCell(2).value = `${rows.length} 条明细`;

  total.getCell(6).value = excelFormula(
    `SUM(F${FIRST_DATA_ROW}:F${lastDataRow})`,
    sum(rows.map(x => x.count))
  );

  total.getCell(7).value = excelFormula(
    `SUM(G${FIRST_DATA_ROW}:G${lastDataRow})`,
    sum(rows.map(x => x.totalArea))
  );

  total.getCell(10).value = excelFormula(
    `SUM(J${FIRST_DATA_ROW}:J${lastDataRow})`,
    sum(rows.map(x => x.totalMass))
  );

  total.getCell(6).numFmt = INT;
  total.getCell(7).numFmt = NUM;
  total.getCell(10).numFmt = NUM;

  if (rows.length > 0) {
    styleBody(ws, FIRST_DATA_ROW, lastDataRow, 11);

    // Apply specialized styles after general body styling.
    rows.forEach((item, index) => {
      const row = ws.getRow(FIRST_DATA_ROW + index);

      row.getCell(2).font = {
        name: FONT,
        size: 9,
        bold: true,
        color: { argb: C.navy },
      };

      row.getCell(11).font = {
        name: FONT,
        size: 8,
        color: { argb: C.muted },
      };

      // Missing-value indicators.
      const missingCells = [
        { col: 3, missing: item.length === null },
        { col: 4, missing: item.material === "未指定" },
        { col: 5, missing: item.area === null },
        { col: 9, missing: item.mass === null },
      ];

      for (const entry of missingCells) {
        if (entry.missing) {
          row.getCell(entry.col).fill = {
            type: "pattern",
            pattern: "solid",
            fgColor: { argb: C.amberLight },
          };

          row.getCell(entry.col).font = {
            name: FONT,
            size: 9,
            color: { argb: C.amber },
          };
        }
      }
    });

    ws.autoFilter = {
      from: { row: headerRow, column: 1 },
      to: { row: lastDataRow, column: 11 },
    };
  }

  styleTotal(total, 11);

  ws.views = [{
    state: "frozen",
    xSplit: 2,
    ySplit: headerRow,
    topLeftCell: "C6",
    activeCell: "C6",
    showGridLines: false,
  }];

  ws.pageSetup.printTitlesRow = "1:5";
  ws.pageSetup.printArea = `A1:K${totalRowNumber}`;
}

/* =========================================================
   SHEET 3 — Material Summary
   ========================================================= */

function createMaterialSummary(
  workbook: ExcelJS.Workbook,
  groups: MaterialGroup[],
  detailRows: NormalizedRow[]
): void {
  const ws = workbook.addWorksheet(SHEET.material);

  setupSheet(ws, C.green);

  ws.columns = [
    { width: 24 },
    { width: 15 },
    { width: 15 },
    { width: 18 },
    { width: 18 },
    { width: 18 },
  ];

  setTitle(
    ws,
    "材料用量汇总",
    "按材质自动归集 BOM 明细，辅助采购计划、材料核算与生产备料",
    6
  );

  const header = ws.getRow(5);

  header.values = [
    "材质",
    "明细行数",
    "构件总数量",
    "总面积 (m²)",
    "总重量 (kg)",
    "重量占比",
  ];

  styleHeader(header);

  const totalMass = sum(groups.map(x => x.mass));
  const lastDetail = FIRST_DATA_ROW + detailRows.length - 1;

  groups.forEach((item, index) => {
    const r = 6 + index;

    const materialCell = ws.getCell(r, 1);
    materialCell.value = item.material;

    ws.getCell(r, 2).value = excelFormula(
      `COUNTIF('${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},A${r})`,
      item.lineCount
    );

    ws.getCell(r, 3).value = excelFormula(
      `SUMIF('${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},A${r},'${SHEET.detail}'!$F$${FIRST_DATA_ROW}:$F$${lastDetail})`,
      item.quantity
    );

    ws.getCell(r, 4).value = excelFormula(
      `SUMIF('${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},A${r},'${SHEET.detail}'!$G$${FIRST_DATA_ROW}:$G$${lastDetail})`,
      item.area
    );

    ws.getCell(r, 5).value = excelFormula(
      `SUMIF('${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},A${r},'${SHEET.detail}'!$J$${FIRST_DATA_ROW}:$J$${lastDetail})`,
      item.mass
    );

    ws.getCell(r, 6).value = excelFormula(
      `IFERROR(E${r}/SUM(E$6:E$${5 + groups.length}),0)`,
      totalMass > 0 ? item.mass / totalMass : 0
    );
  });

  const totalRowNumber = 6 + groups.length;
  const total = ws.getRow(totalRowNumber);

  total.getCell(1).value = "合计";

  total.getCell(2).value = excelFormula(
    `SUM(B6:B${totalRowNumber - 1})`,
    sum(groups.map(x => x.lineCount))
  );

  total.getCell(3).value = excelFormula(
    `SUM(C6:C${totalRowNumber - 1})`,
    sum(groups.map(x => x.quantity))
  );

  total.getCell(4).value = excelFormula(
    `SUM(D6:D${totalRowNumber - 1})`,
    sum(groups.map(x => x.area))
  );

  total.getCell(5).value = excelFormula(
    `SUM(E6:E${totalRowNumber - 1})`,
    totalMass
  );

  total.getCell(6).value = excelFormula(
    `IFERROR(E${totalRowNumber}/E${totalRowNumber},0)`,
    totalMass > 0 ? 1 : 0
  );

  if (groups.length > 0) {
    styleBody(ws, 6, totalRowNumber - 1, 6);

    ws.autoFilter = {
      from: { row: 5, column: 1 },
      to: { row: totalRowNumber - 1, column: 6 },
    };
  } else {
    addEmptyState(ws, 6, 6, "暂无材料汇总数据");
  }

  for (let r = 6; r <= totalRowNumber; r++) {
    setNumberFormat(ws, r, [2, 3], INT);
    setNumberFormat(ws, r, [4, 5], NUM);
    setNumberFormat(ws, r, [6], PCT);
  }

  styleTotal(total, 6);

  ws.views = [{
    state: "frozen",
    ySplit: 5,
    topLeftCell: "A6",
    showGridLines: false,
  }];

  ws.pageSetup.printTitlesRow = "1:5";
  ws.pageSetup.printArea = `A1:F${totalRowNumber}`;
}

/* =========================================================
   SHEET 4 — Specification Summary
   ========================================================= */

function createSpecificationSummary(
  workbook: ExcelJS.Workbook,
  groups: SpecificationGroup[],
  detailRows: NormalizedRow[]
): void {
  const ws = workbook.addWorksheet(SHEET.specification);

  setupSheet(ws, C.amber);

  ws.columns = [
    { width: 28 },
    { width: 15 },
    { width: 18 },
    { width: 14 },
    { width: 14 },
    { width: 18 },
    { width: 18 },
  ];

  setTitle(
    ws,
    "构件规格汇总",
    "按构件名称、长度与材质归并相同规格，便于核对生产批次",
    7
  );

  const header = ws.getRow(5);

  header.values = [
    "构件名称",
    "长度 (mm)",
    "材质",
    "明细行数",
    "构件数量",
    "总面积 (m²)",
    "总重量 (kg)",
  ];

  styleHeader(header);

  const lastDetail = FIRST_DATA_ROW + detailRows.length - 1;

  groups.forEach((item, index) => {
    const r = 6 + index;

    ws.getCell(r, 1).value = item.caption;
    ws.getCell(r, 2).value = item.length;
    ws.getCell(r, 3).value = item.material;

    const criteriaLength = item.length === null
      ? `B${r}=""`
      : `'${SHEET.detail}'!$C$${FIRST_DATA_ROW}:$C$${lastDetail},B${r}`;

    const countFormula = item.length === null
      ? `COUNTIFS('${SHEET.detail}'!$B$${FIRST_DATA_ROW}:$B$${lastDetail},A${r},'${SHEET.detail}'!$C$${FIRST_DATA_ROW}:$C$${lastDetail},"",'${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},C${r})`
      : `COUNTIFS('${SHEET.detail}'!$B$${FIRST_DATA_ROW}:$B$${lastDetail},A${r},'${SHEET.detail}'!$C$${FIRST_DATA_ROW}:$C$${lastDetail},B${r},'${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},C${r})`;

    const quantityFormula = item.length === null
      ? `SUMIFS('${SHEET.detail}'!$F$${FIRST_DATA_ROW}:$F$${lastDetail},'${SHEET.detail}'!$B$${FIRST_DATA_ROW}:$B$${lastDetail},A${r},'${SHEET.detail}'!$C$${FIRST_DATA_ROW}:$C$${lastDetail},"",'${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},C${r})`
      : `SUMIFS('${SHEET.detail}'!$F$${FIRST_DATA_ROW}:$F$${lastDetail},'${SHEET.detail}'!$B$${FIRST_DATA_ROW}:$B$${lastDetail},A${r},'${SHEET.detail}'!$C$${FIRST_DATA_ROW}:$C$${lastDetail},B${r},'${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},C${r})`;

    const areaFormula = item.length === null
      ? `SUMIFS('${SHEET.detail}'!$G$${FIRST_DATA_ROW}:$G$${lastDetail},'${SHEET.detail}'!$B$${FIRST_DATA_ROW}:$B$${lastDetail},A${r},'${SHEET.detail}'!$C$${FIRST_DATA_ROW}:$C$${lastDetail},"",'${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},C${r})`
      : `SUMIFS('${SHEET.detail}'!$G$${FIRST_DATA_ROW}:$G$${lastDetail},'${SHEET.detail}'!$B$${FIRST_DATA_ROW}:$B$${lastDetail},A${r},'${SHEET.detail}'!$C$${FIRST_DATA_ROW}:$C$${lastDetail},B${r},'${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},C${r})`;

    const massFormula = item.length === null
      ? `SUMIFS('${SHEET.detail}'!$J$${FIRST_DATA_ROW}:$J$${lastDetail},'${SHEET.detail}'!$B$${FIRST_DATA_ROW}:$B$${lastDetail},A${r},'${SHEET.detail}'!$C$${FIRST_DATA_ROW}:$C$${lastDetail},"",'${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},C${r})`
      : `SUMIFS('${SHEET.detail}'!$J$${FIRST_DATA_ROW}:$J$${lastDetail},'${SHEET.detail}'!$B$${FIRST_DATA_ROW}:$B$${lastDetail},A${r},'${SHEET.detail}'!$C$${FIRST_DATA_ROW}:$C$${lastDetail},B${r},'${SHEET.detail}'!$D$${FIRST_DATA_ROW}:$D$${lastDetail},C${r})`;

    ws.getCell(r, 4).value = excelFormula(
      countFormula,
      item.lineCount
    );

    ws.getCell(r, 5).value = excelFormula(
      quantityFormula,
      item.quantity
    );

    ws.getCell(r, 6).value = excelFormula(
      areaFormula,
      item.area
    );

    ws.getCell(r, 7).value = excelFormula(
      massFormula,
      item.mass
    );
  });

  const totalRowNumber = 6 + groups.length;
  const total = ws.getRow(totalRowNumber);

  total.getCell(1).value = "合计";

  total.getCell(4).value = excelFormula(
    `SUM(D6:D${totalRowNumber - 1})`,
    sum(groups.map(x => x.lineCount))
  );

  total.getCell(5).value = excelFormula(
    `SUM(E6:E${totalRowNumber - 1})`,
    sum(groups.map(x => x.quantity))
  );

  total.getCell(6).value = excelFormula(
    `SUM(F6:F${totalRowNumber - 1})`,
    sum(groups.map(x => x.area))
  );

  total.getCell(7).value = excelFormula(
    `SUM(G6:G${totalRowNumber - 1})`,
    sum(groups.map(x => x.mass))
  );

  if (groups.length > 0) {
    styleBody(ws, 6, totalRowNumber - 1, 7);

    ws.autoFilter = {
      from: { row: 5, column: 1 },
      to: { row: totalRowNumber - 1, column: 7 },
    };
  } else {
    addEmptyState(ws, 6, 7, "暂无规格汇总数据");
  }

  for (let r = 6; r <= totalRowNumber; r++) {
    setNumberFormat(ws, r, [2, 6, 7], NUM);
    setNumberFormat(ws, r, [4, 5], INT);
  }

  styleTotal(total, 7);

  ws.views = [{
    state: "frozen",
    ySplit: 5,
    topLeftCell: "A6",
    showGridLines: false,
  }];

  ws.pageSetup.printTitlesRow = "1:5";
  ws.pageSetup.printArea = `A1:G${totalRowNumber}`;
}

/* =========================================================
   SHEET 5 — Field Definitions and Instructions
   ========================================================= */

function createFieldGuide(workbook: ExcelJS.Workbook): void {
  const ws = workbook.addWorksheet(SHEET.guide);

  setupSheet(ws, C.muted);

  ws.columns = [
    { width: 23 },
    { width: 23 },
    { width: 58 },
    { width: 25 },
  ];

  setTitle(
    ws,
    "字段定义与使用说明",
    "本工作簿由 SteelMind AI 根据 BomElement 数据结构自动生成，不依赖外部 Excel 模板",
    4
  );

  section(ws, 5, 1, 4, "BOM 明细字段定义");

  const header = ws.getRow(6);

  header.values = [
    "程序字段",
    "Excel 列名",
    "含义 / 计算说明",
    "数据来源",
  ];

  styleHeader(header);

  const definitions = [
    [
      "caption",
      "构件名称",
      "CAD 解析得到的构件名称或图元描述。",
      "BomElement.caption",
    ],
    [
      "length",
      "长度 (mm)",
      "构件长度，单位为 mm。",
      "BomElement.length",
    ],
    [
      "material",
      "材质",
      "构件材质；未提供时显示为“未指定”。",
      "BomElement.material",
    ],
    [
      "area",
      "单件面积 (m²)",
      "单个构件的面积，单位为 m²。",
      "BomElement.area",
    ],
    [
      "count",
      "数量",
      "该 BOM 明细对应的构件数量。",
      "BomElement.count",
    ],
    [
      "totalArea",
      "合计面积 (m²)",
      "单件面积 × 数量。",
      "Excel 公式",
    ],
    [
      "volume",
      "单件体积 (m³)",
      "单个构件的体积，单位为 m³。",
      "BomElement.volume",
    ],
    [
      "mass",
      "单件重量 (kg)",
      "单个构件的重量，单位为 kg。",
      "BomElement.mass",
    ],
    [
      "totalMass",
      "合计重量 (kg)",
      "单件重量 × 数量。",
      "Excel 公式",
    ],
    [
      "source_handles",
      "CAD 实体句柄",
      "关联的 CAD 实体句柄；多个句柄以逗号分隔。",
      "BomElement.source_handles",
    ],
  ];

  definitions.forEach((values, index) => {
    const row = ws.getRow(7 + index);

    row.values = values;
    row.height = 34;

    row.eachCell({ includeEmpty: true }, (cell, col) => {
      cell.font = {
        name: FONT,
        size: 9,
        bold: col === 1,
        color: {
          argb: col === 1 ? C.navy : C.ink,
        },
      };

      cell.fill = {
        type: "pattern",
        pattern: "solid",
        fgColor: {
          argb: index % 2 === 0 ? C.white : C.alternate,
        },
      };

      cell.alignment = {
        vertical: "middle",
        wrapText: true,
      };

      cell.border = {
        bottom: {
          style: "thin",
          color: { argb: C.border },
        },
      };
    });
  });

  section(ws, 19, 1, 4, "统计口径与注意事项");

  const notes = [
    [
      "面积统计",
      "总面积 = Σ(单件面积 × 数量)。缺失的单件面积按 0 计入，并在项目总览中提示。",
    ],
    [
      "重量统计",
      "总重量 = Σ(单件重量 × 数量)。缺失的单件重量按 0 计入，并在项目总览中提示。",
    ],
    [
      "规格归并",
      "规格汇总按构件名称、长度和材质三个字段组合归并。",
    ],
    [
      "材料归并",
      "材料汇总按材质字段归并；未填写材质的项目统一归入“未指定”。",
    ],
    [
      "数据复核",
      "本文件反映 CAD 智能解析结果。下料、采购及生产前，应由工程人员核对图纸、材质和计量口径。",
    ],
    [
      "公式更新",
      "明细合计面积、合计重量及汇总数据使用 Excel 公式。修改明细数据后，Excel 可重新计算关联统计。",
    ],
    [
      "数据验证",
      "负数或非数值的长度、面积、体积和重量会被视为缺失值，不参与用量计算。",
    ],
  ];

  notes.forEach(([label, description], index) => {
    const r = 20 + index;

    ws.mergeCells(r, 1, r, 2);
    ws.mergeCells(r, 3, r, 4);

    ws.getCell(r, 1).value = label;
    ws.getCell(r, 3).value = description;

    ws.getCell(r, 1).font = {
      name: FONT,
      size: 9,
      bold: true,
      color: { argb: C.navy },
    };

    ws.getCell(r, 3).font = {
      name: FONT,
      size: 9,
      color: { argb: C.ink },
    };

    ws.getCell(r, 1).fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: C.blueLight },
    };

    ws.getCell(r, 3).fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: C.white },
    };

    ws.getCell(r, 1).alignment = {
      vertical: "middle",
      indent: 1,
    };

    ws.getCell(r, 3).alignment = {
      vertical: "middle",
      wrapText: true,
      indent: 1,
    };

    ws.getRow(r).height = 38;

    for (let col = 1; col <= 4; col++) {
      ws.getCell(r, col).border = {
        bottom: {
          style: "thin",
          color: { argb: C.border },
        },
      };
    }
  });

  ws.views = [{
    state: "frozen",
    ySplit: 6,
    topLeftCell: "A7",
    showGridLines: false,
  }];

  ws.pageSetup.printArea = "A1:D26";
}

/* -------------------- Workbook metadata -------------------- */

function configureWorkbook(workbook: ExcelJS.Workbook): void {
  workbook.creator = "SteelMind AI";
  workbook.lastModifiedBy = "SteelMind AI";
  workbook.title = "钢格板智能制造综合 BOM";
  workbook.subject = "CAD 智能解析钢格板 BOM";
  workbook.created = new Date();
  workbook.modified = new Date();

  // Do not assign unsupported CalculationProperties fields.
  // Formula cells include cached results for initial display.
}

/* -------------------- Browser download -------------------- */

function downloadExcel(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  window.setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 1000);
}

/* =========================================================
   PUBLIC API
   Preserve the original function signature.
   ========================================================= */

export async function export2Xlsx(
  bomElements: BomElement[]
): Promise<void> {
  if (
    typeof window === "undefined" ||
    typeof document === "undefined"
  ) {
    throw new Error("Excel 导出必须在浏览器端执行。");
  }

  if (!Array.isArray(bomElements) || bomElements.length === 0) {
    throw new Error("当前没有可导出的 BOM 数据。");
  }

  const rows = normalizeData(bomElements);

  const materials = groupMaterials(rows);
  const specifications = groupSpecifications(rows);

  const workbook = new ExcelJS.Workbook();

  configureWorkbook(workbook);

  // Create detail first so all other sheets can reference it.
  createBomDetail(workbook, rows);

  createMaterialSummary(workbook, materials, rows);

  createSpecificationSummary(workbook, specifications, rows);

  createOverview(
    workbook,
    rows,
    materials,
    specifications
  );

  createFieldGuide(workbook);

  const buffer = await workbook.xlsx.writeBuffer();

  const blob = new Blob(
    [buffer as BlobPart],
    {
      type:
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
  );

  const date = new Date().toISOString().slice(0, 10);

  downloadExcel(
    blob,
    `SteelMind_AI_钢格板综合BOM_${date}.xlsx`
  );
}
