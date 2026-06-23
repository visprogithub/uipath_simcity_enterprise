import * as PIXI from 'pixi.js';
import type {
  SimulationState,
  Building,
  BuildingType,
  BuildingStatus,
  Workflow,
  Agent,
  AgentType,
  OverlayMode,
} from '@shared/index';

// ─── Constants ────────────────────────────────────────────────────────────────

const TILE_SIZE = 32;
const GRID_W = 32;
const GRID_H = 20;
export const CANVAS_W = GRID_W * TILE_SIZE; // 1024
export const CANVAS_H = GRID_H * TILE_SIZE; // 640

const BUILDING_COLORS: Record<BuildingType, number> = {
  hospital: 0x1a5f7a,
  pharmacy: 0x1a7a5f,
  cloud_datacenter: 0x4a1a7a,
  comms_hub: 0x7a4a1a,
  orchestration_center: 0x1a7a7a,
  staffing_hr: 0x3a7a1a,
  backup_infra: 0x4a4a4a,
};

const WORKFLOW_COLORS: Record<string, number> = {
  ehr_record: 0x0088ff,
  prescription: 0x00ffaa,
  comm_packet: 0xff8800,
  approval_request: 0xffff00,
  escalation: 0xff0000,
  failover_cmd: 0xffffff,
  staffing_request: 0xcc44ff,
};

const AGENT_COLORS: Record<AgentType, number> = {
  operations_coordinator: 0x00ffff,
  incident_response: 0xff4444,
  compliance: 0xffd700,
  communications: 0x44ff44,
  executive_strategy: 0xcc44ff,
};

// ─── CityRenderer class ───────────────────────────────────────────────────────

export class CityRenderer {
  private app: PIXI.Application;
  private backgroundLayer: PIXI.Container;
  private connectionLayer: PIXI.Container;
  private buildingLayer: PIXI.Container;
  private workflowLayer: PIXI.Container;
  private agentLayer: PIXI.Container;
  private overlayLayer: PIXI.Container;
  private uiLayer: PIXI.Container;

  private buildingGraphics: Map<string, PIXI.Container> = new Map();
  private connectionGraphics: Map<string, PIXI.Graphics> = new Map();
  private workflowSprites: Map<string, PIXI.Container> = new Map();
  private agentSprites: Map<string, PIXI.Container> = new Map();
  private reroutedLinesGraphics: PIXI.Graphics | null = null;

  private buildingClickCallback: ((id: string) => void) | null = null;
  private agentClickCallback: ((id: string) => void) | null = null;

  private animationTime = 0;
  private gridBg: PIXI.Graphics | null = null;

  // Workflow packet positions (interpolated)
  private workflowPositions: Map<string, { x: number; y: number; angle: number }> = new Map();

  // Rerouted flash tracking: wfId -> { tick: number, flashCount: number }
  private reroutedFlash: Map<string, { startTime: number }> = new Map();
  private prevWorkflowStatuses: Map<string, string> = new Map();

  // Agent drone positions (interpolated towards target)
  private agentPositions: Map<string, { x: number; y: number }> = new Map();

  private lastState: SimulationState | null = null;

  constructor(canvas: HTMLCanvasElement) {
    this.app = new PIXI.Application({
      view: canvas,
      width: CANVAS_W,
      height: CANVAS_H,
      backgroundColor: 0x0a0e1a,
      antialias: true,
      resolution: 1,
    });

    this.backgroundLayer = new PIXI.Container();
    this.connectionLayer = new PIXI.Container();
    this.buildingLayer = new PIXI.Container();
    this.workflowLayer = new PIXI.Container();
    this.agentLayer = new PIXI.Container();
    this.overlayLayer = new PIXI.Container();
    this.uiLayer = new PIXI.Container();

    this.app.stage.addChild(this.backgroundLayer);
    this.app.stage.addChild(this.connectionLayer);
    this.app.stage.addChild(this.buildingLayer);
    this.app.stage.addChild(this.workflowLayer);
    this.app.stage.addChild(this.agentLayer);
    this.app.stage.addChild(this.overlayLayer);
    this.app.stage.addChild(this.uiLayer);
  }

  init(): void {
    this.drawGrid();

    // Create rerouted lines graphics (drawn below workflow sprites)
    this.reroutedLinesGraphics = new PIXI.Graphics();
    this.workflowLayer.addChildAt(this.reroutedLinesGraphics, 0);

    // Add a ticker for animations
    this.app.ticker.add((delta: number) => {
      this.animationTime += delta * 0.016; // Convert to seconds approximately
      this.tickAnimations();
    });
  }

  // ─── Public update ──────────────────────────────────────────────────────────

  update(state: SimulationState, overlay: OverlayMode): void {
    this.lastState = state;
    this.updateBuildings(state.buildings);
    this.updateConnections(state.buildings);
    this.updateWorkflows(state.workflows, state.buildings);
    this.updateAgents(state.agents, state.buildings);
    this.updateOverlay(state, overlay);
  }

  // ─── Grid ───────────────────────────────────────────────────────────────────

  private drawGrid(): void {
    this.backgroundLayer.removeChildren();

    const bg = new PIXI.Graphics();
    bg.beginFill(0x0a0e1a);
    bg.drawRect(0, 0, CANVAS_W, CANVAS_H);
    bg.endFill();

    // Grid lines
    bg.lineStyle(1, 0x1a2035, 0.5);
    for (let x = 0; x <= GRID_W; x++) {
      bg.moveTo(x * TILE_SIZE, 0);
      bg.lineTo(x * TILE_SIZE, CANVAS_H);
    }
    for (let y = 0; y <= GRID_H; y++) {
      bg.moveTo(0, y * TILE_SIZE);
      bg.lineTo(CANVAS_W, y * TILE_SIZE);
    }

    this.backgroundLayer.addChild(bg);
    this.gridBg = bg;

    // Road-like paths between common areas
    const roads = new PIXI.Graphics();
    roads.beginFill(0x111825, 0.8);
    // Horizontal main road
    roads.drawRect(0, 9 * TILE_SIZE, CANVAS_W, 2 * TILE_SIZE);
    // Vertical main road
    roads.drawRect(15 * TILE_SIZE, 0, 2 * TILE_SIZE, CANVAS_H);
    roads.endFill();

    // Road markings
    roads.lineStyle(1, 0x1e2d4a, 0.6);
    roads.moveTo(0, 10 * TILE_SIZE);
    roads.lineTo(CANVAS_W, 10 * TILE_SIZE);
    roads.moveTo(16 * TILE_SIZE, 0);
    roads.lineTo(16 * TILE_SIZE, CANVAS_H);

    this.backgroundLayer.addChild(roads);
  }

  // ─── Buildings ─────────────────────────────────────────────────────────────

  private updateBuildings(buildings: Building[]): void {
    const seen = new Set<string>();

    for (const building of buildings) {
      seen.add(building.id);
      let container = this.buildingGraphics.get(building.id);

      if (!container) {
        container = this.createBuildingContainer(building);
        this.buildingGraphics.set(building.id, container);
        this.buildingLayer.addChild(container);
      }

      this.renderBuilding(container, building);
    }

    // Remove stale buildings
    for (const [id, container] of this.buildingGraphics) {
      if (!seen.has(id)) {
        this.buildingLayer.removeChild(container);
        container.destroy({ children: true });
        this.buildingGraphics.delete(id);
      }
    }
  }

  private createBuildingContainer(building: Building): PIXI.Container {
    const container = new PIXI.Container();
    container.interactive = true;
    container.cursor = 'pointer';
    container.on('pointerdown', () => {
      this.buildingClickCallback?.(building.id);
    });
    return container;
  }

  private renderBuilding(container: PIXI.Container, building: Building): void {
    container.removeChildren();

    const pos = this.getTilePos(building.pos.x, building.pos.y);
    const w = building.pos.w * TILE_SIZE;
    const h = building.pos.h * TILE_SIZE;
    container.x = pos.x;
    container.y = pos.y;

    const baseColor = BUILDING_COLORS[building.type] ?? 0x333333;

    // Status modifiers
    let alpha = 1.0;
    let borderColor = baseColor;
    let borderWidth = 2;

    switch (building.status) {
      case 'operational':
        alpha = 1.0;
        borderColor = 0x00aaff;
        borderWidth = 1;
        break;
      case 'degraded':
        alpha = 0.7;
        borderColor = 0xffaa00;
        borderWidth = 2;
        break;
      case 'critical':
        alpha = 0.45;
        borderColor = 0xff4444;
        borderWidth = 3;
        break;
      case 'offline':
        alpha = 0.2;
        borderColor = 0x220000;
        borderWidth = 3;
        break;
    }

    // Outer glow / shadow for operational
    if (building.status === 'operational') {
      const glow = new PIXI.Graphics();
      glow.beginFill(baseColor, 0.15);
      glow.drawRoundedRect(-4, -4, w + 8, h + 8, 6);
      glow.endFill();
      container.addChild(glow);
    }

    // Main body
    const body = new PIXI.Graphics();
    body.lineStyle(borderWidth, borderColor, 0.9);
    body.beginFill(baseColor, alpha);
    body.drawRoundedRect(0, 0, w, h, 4);
    body.endFill();
    container.addChild(body);

    // Inner highlight
    const highlight = new PIXI.Graphics();
    highlight.beginFill(0xffffff, 0.05);
    highlight.drawRoundedRect(2, 2, w - 4, 8, 2);
    highlight.endFill();
    container.addChild(highlight);

    // Symbol / icon — prefer the building's own emoji (scenario-specific); fall back to type glyph
    if (building.icon) {
      const icon = new PIXI.Text(building.icon, { fontSize: Math.min(w, h) * 0.42 });
      icon.anchor.set(0.5);
      icon.x = w / 2;
      icon.y = h / 2 - 6;
      container.addChild(icon);
    } else {
      this.drawBuildingSymbol(container, building.type, w, h);
    }

    // Name label
    const label = new PIXI.Text(building.name, {
      fontSize: 9,
      fill: 0xe8f0ff,
      fontWeight: 'bold',
      wordWrap: true,
      wordWrapWidth: w - 4,
      align: 'center',
    });
    label.x = Math.floor((w - label.width) / 2);
    label.y = h - 18;
    container.addChild(label);

    // Health bar at bottom
    const barBg = new PIXI.Graphics();
    barBg.beginFill(0x000000, 0.5);
    barBg.drawRect(2, h - 6, w - 4, 4);
    barBg.endFill();
    container.addChild(barBg);

    const healthColor = building.health > 60 ? 0x44ff88 : building.health > 30 ? 0xffaa00 : 0xff4444;
    const barFill = new PIXI.Graphics();
    barFill.beginFill(healthColor, 0.9);
    barFill.drawRect(2, h - 6, ((w - 4) * building.health) / 100, 4);
    barFill.endFill();
    container.addChild(barFill);

    // Offline X mark
    if (building.status === 'offline') {
      const x = new PIXI.Graphics();
      x.lineStyle(3, 0xff2222, 0.8);
      x.moveTo(8, 8);
      x.lineTo(w - 8, h - 8);
      x.moveTo(w - 8, 8);
      x.lineTo(8, h - 8);
      container.addChild(x);
    }
  }

  private drawBuildingSymbol(
    container: PIXI.Container,
    type: BuildingType,
    w: number,
    h: number
  ): void {
    const g = new PIXI.Graphics();
    const cx = w / 2;
    const cy = h / 2 - 6;
    const s = Math.min(w, h) * 0.22;

    switch (type) {
      case 'hospital':
        // Red cross
        g.beginFill(0xff3333, 0.9);
        g.drawRect(cx - s * 0.3, cy - s, s * 0.6, s * 2);
        g.drawRect(cx - s, cy - s * 0.3, s * 2, s * 0.6);
        g.endFill();
        break;

      case 'pharmacy':
        // Pill shape
        g.beginFill(0x44ffcc, 0.9);
        g.drawCircle(cx - s * 0.4, cy, s * 0.55);
        g.drawCircle(cx + s * 0.4, cy, s * 0.55);
        g.drawRect(cx - s * 0.4, cy - s * 0.55, s * 0.8, s * 1.1);
        g.endFill();
        g.beginFill(0x004444, 0.8);
        g.drawRect(cx - s * 0.08, cy - s * 0.55, s * 0.16, s * 1.1);
        g.endFill();
        break;

      case 'cloud_datacenter':
        // Cloud shape
        g.beginFill(0xcc88ff, 0.9);
        g.drawCircle(cx, cy - s * 0.2, s * 0.6);
        g.drawCircle(cx - s * 0.5, cy + s * 0.1, s * 0.45);
        g.drawCircle(cx + s * 0.5, cy + s * 0.1, s * 0.45);
        g.drawRect(cx - s * 0.9, cy + s * 0.1, s * 1.8, s * 0.5);
        g.endFill();
        break;

      case 'comms_hub':
        // Antenna / signal waves
        g.lineStyle(3, 0xffaa44, 0.9);
        g.moveTo(cx, cy + s * 0.8);
        g.lineTo(cx, cy - s * 0.8);
        // Signal waves
        for (let i = 1; i <= 2; i++) {
          const r = s * 0.4 * i;
          g.arc(cx, cy, r, -Math.PI * 0.75, -Math.PI * 0.25);
        }
        break;

      case 'orchestration_center':
        // Circuit board pattern
        g.lineStyle(2, 0x44ffff, 0.9);
        g.drawRect(cx - s * 0.6, cy - s * 0.6, s * 1.2, s * 1.2);
        g.moveTo(cx - s * 0.6, cy);
        g.lineTo(cx - s, cy);
        g.moveTo(cx + s * 0.6, cy);
        g.lineTo(cx + s, cy);
        g.moveTo(cx, cy - s * 0.6);
        g.lineTo(cx, cy - s);
        g.moveTo(cx, cy + s * 0.6);
        g.lineTo(cx, cy + s);
        g.beginFill(0x44ffff, 0.6);
        g.drawCircle(cx, cy, s * 0.25);
        g.endFill();
        break;

      case 'staffing_hr':
        // People silhouettes
        g.beginFill(0x88ff44, 0.9);
        g.drawCircle(cx - s * 0.4, cy - s * 0.4, s * 0.3);
        g.drawCircle(cx + s * 0.4, cy - s * 0.4, s * 0.3);
        g.drawEllipse(cx - s * 0.4, cy + s * 0.2, s * 0.3, s * 0.5);
        g.drawEllipse(cx + s * 0.4, cy + s * 0.2, s * 0.3, s * 0.5);
        g.endFill();
        break;

      case 'backup_infra':
        // Shield shape
        g.beginFill(0xaaaaaa, 0.8);
        g.moveTo(cx, cy - s);
        g.lineTo(cx + s * 0.8, cy - s * 0.4);
        g.lineTo(cx + s * 0.8, cy + s * 0.2);
        g.lineTo(cx, cy + s);
        g.lineTo(cx - s * 0.8, cy + s * 0.2);
        g.lineTo(cx - s * 0.8, cy - s * 0.4);
        g.closePath();
        g.endFill();
        g.lineStyle(2, 0xffffff, 0.5);
        g.moveTo(cx - s * 0.3, cy);
        g.lineTo(cx, cy + s * 0.4);
        g.lineTo(cx + s * 0.4, cy - s * 0.4);
        break;
    }

    container.addChild(g);
  }

  // ─── Connections ────────────────────────────────────────────────────────────

  private updateConnections(buildings: Building[]): void {
    // Clear all connection graphics
    for (const g of this.connectionGraphics.values()) {
      this.connectionLayer.removeChild(g);
      g.destroy();
    }
    this.connectionGraphics.clear();

    const buildingMap = new Map(buildings.map((b) => [b.id, b]));

    for (const building of buildings) {
      for (const depId of building.dependencies) {
        const dep = buildingMap.get(depId);
        if (!dep) continue;

        const key = `${building.id}:${depId}`;
        const lineG = new PIXI.Graphics();

        const src = this.getBuildingCenter(building);
        const dst = this.getBuildingCenter(dep);

        // Color by status
        let lineColor = 0x00aaff;
        let lineAlpha = 0.45;

        if (
          building.status === 'offline' ||
          dep.status === 'offline'
        ) {
          lineColor = 0xff2222;
          lineAlpha = 0.7;
        } else if (
          building.status === 'critical' ||
          dep.status === 'critical'
        ) {
          lineColor = 0xff4444;
          lineAlpha = 0.6;
        } else if (
          building.status === 'degraded' ||
          dep.status === 'degraded'
        ) {
          lineColor = 0xff8800;
          lineAlpha = 0.55;
        }

        // Draw animated dashed line
        this.drawDashedLine(lineG, src.x, src.y, dst.x, dst.y, lineColor, lineAlpha);

        this.connectionLayer.addChild(lineG);
        this.connectionGraphics.set(key, lineG);
      }
    }
  }

  private drawDashedLine(
    g: PIXI.Graphics,
    x1: number,
    y1: number,
    x2: number,
    y2: number,
    color: number,
    alpha: number
  ): void {
    const dashLen = 8;
    const gapLen = 6;
    const dx = x2 - x1;
    const dy = y2 - y1;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 1) return;

    const ux = dx / dist;
    const uy = dy / dist;

    // Offset by animation time for "moving" effect
    const offset = (this.animationTime * 20) % (dashLen + gapLen);

    g.lineStyle(1.5, color, alpha);

    let pos = -offset;
    while (pos < dist) {
      const startPos = Math.max(0, pos);
      const endPos = Math.min(dist, pos + dashLen);
      if (endPos > startPos) {
        g.moveTo(x1 + ux * startPos, y1 + uy * startPos);
        g.lineTo(x1 + ux * endPos, y1 + uy * endPos);
      }
      pos += dashLen + gapLen;
    }
  }

  // ─── Workflows ──────────────────────────────────────────────────────────────

  private updateWorkflows(workflows: Workflow[], buildings: Building[]): void {
    const seen = new Set<string>();
    const buildingMap = new Map(buildings.map((b) => [b.id, b]));

    // Keep only flowing, queued, rerouted workflows visible
    const activeWorkflows = workflows.filter(
      (w) => w.status !== 'failed' && w.status !== 'escalated'
    );

    for (const wf of activeWorkflows) {
      seen.add(wf.id);

      const src = buildingMap.get(wf.sourceId);
      const dst = buildingMap.get(wf.destId);
      if (!src || !dst) continue;

      // Detect new rerouted transition -> start flash
      const prevStatus = this.prevWorkflowStatuses.get(wf.id);
      if (wf.status === 'rerouted' && prevStatus !== 'rerouted') {
        this.reroutedFlash.set(wf.id, { startTime: this.animationTime });
      }
      this.prevWorkflowStatuses.set(wf.id, wf.status);

      let container = this.workflowSprites.get(wf.id);
      if (!container) {
        container = this.createWorkflowSprite(wf.type, wf.status === 'rerouted');
        this.workflowSprites.set(wf.id, container);
        this.workflowLayer.addChild(container);
      } else if (wf.status === 'rerouted') {
        // Recolor existing sprite to orange
        this.recolorWorkflowSpriteOrange(container);
      }

      this.positionWorkflowSprite(container, wf, src, dst);
    }

    // Remove stale
    for (const [id, container] of this.workflowSprites) {
      if (!seen.has(id)) {
        this.workflowLayer.removeChild(container);
        container.destroy({ children: true });
        this.workflowSprites.delete(id);
        this.reroutedFlash.delete(id);
        this.prevWorkflowStatuses.delete(id);
      }
    }

    // Draw orange dashed lines for rerouted workflows
    this.drawReroutedLines(activeWorkflows, buildingMap);
  }

  private drawReroutedLines(workflows: Workflow[], buildingMap: Map<string, Building>): void {
    if (!this.reroutedLinesGraphics) return;
    this.reroutedLinesGraphics.clear();

    for (const wf of workflows) {
      if (wf.status !== 'rerouted') continue;
      const src = buildingMap.get(wf.sourceId);
      const dst = buildingMap.get(wf.destId);
      if (!src || !dst) continue;

      const srcCenter = this.getBuildingCenter(src);
      const dstCenter = this.getBuildingCenter(dst);

      this.drawDashedLine(
        this.reroutedLinesGraphics,
        srcCenter.x, srcCenter.y,
        dstCenter.x, dstCenter.y,
        0xFF6600,
        0.6
      );
    }
  }

  private recolorWorkflowSpriteOrange(container: PIXI.Container): void {
    // Mark container with rerouted flag to skip re-creation churn
    (container as any).__rerouted = true;
  }

  private createWorkflowSprite(type: string, rerouted = false): PIXI.Container {
    const container = new PIXI.Container();

    // Rerouted workflows use orange
    const color = rerouted ? 0xFF6600 : (WORKFLOW_COLORS[type] ?? 0xffffff);
    (container as any).__rerouted = rerouted;

    const g = new PIXI.Graphics();
    // Outer glow
    g.beginFill(color, 0.25);
    g.drawCircle(0, 0, 10);
    g.endFill();
    // Inner circle
    g.beginFill(color, 0.9);
    g.drawCircle(0, 0, 5);
    g.endFill();
    // Center highlight
    g.beginFill(0xffffff, 0.5);
    g.drawCircle(-1, -1, 2);
    g.endFill();

    if (rerouted) {
      // Draw a small orange arrow indicator to distinguish rerouted packets
      const arrow = new PIXI.Graphics();
      arrow.beginFill(0xFF6600, 0.9);
      arrow.moveTo(0, -8);
      arrow.lineTo(4, -4);
      arrow.lineTo(-4, -4);
      arrow.closePath();
      arrow.endFill();
      container.addChild(arrow);
    }

    container.addChild(g);
    return container;
  }

  private positionWorkflowSprite(
    container: PIXI.Container,
    wf: Workflow,
    src: Building,
    dst: Building
  ): void {
    const srcCenter = this.getBuildingCenter(src);
    const dstCenter = this.getBuildingCenter(dst);

    let progress = wf.progress;

    if (wf.status === 'queued') {
      // Cluster near source with small jitter
      const idx = Array.from(this.workflowSprites.keys()).indexOf(wf.id);
      const jitter = (idx % 3) * 10 - 10;
      container.x = srcCenter.x + jitter;
      container.y = srcCenter.y + Math.sin(this.animationTime * 2 + idx) * 4;
      container.alpha = 0.7;
    } else if (wf.status === 'blocked') {
      // Stationary near midpoint, pulsing
      container.x = srcCenter.x + (dstCenter.x - srcCenter.x) * progress;
      container.y = srcCenter.y + (dstCenter.y - srcCenter.y) * progress;
      container.alpha = 0.5 + 0.5 * Math.sin(this.animationTime * 6);
    } else if (wf.status === 'rerouted') {
      // Rerouted - move along path with orange flash effect
      container.x = srcCenter.x + (dstCenter.x - srcCenter.x) * progress;
      container.y = srcCenter.y + (dstCenter.y - srcCenter.y) * progress;

      // Flash effect: pulse 3 times over ~1.5 seconds after reroute transition
      const flashData = this.reroutedFlash.get(wf.id);
      if (flashData) {
        const elapsed = this.animationTime - flashData.startTime;
        const flashDuration = 1.5;
        if (elapsed < flashDuration) {
          // 3 pulses over flashDuration seconds
          container.alpha = 0.5 + 0.5 * Math.abs(Math.sin((elapsed / flashDuration) * Math.PI * 3));
        } else {
          this.reroutedFlash.delete(wf.id);
          container.alpha = 0.85;
        }
      } else {
        container.alpha = 0.85;
      }
    } else {
      // Flowing - move along the path
      container.x = srcCenter.x + (dstCenter.x - srcCenter.x) * progress;
      container.y = srcCenter.y + (dstCenter.y - srcCenter.y) * progress;
      container.alpha = 1.0;
    }

    // Scale by priority
    const scale = wf.priority === 'critical' ? 1.4 : wf.priority === 'high' ? 1.2 : 1.0;
    container.scale.set(scale);
  }

  // ─── Agents ─────────────────────────────────────────────────────────────────

  private updateAgents(agents: Agent[], buildings: Building[]): void {
    const seen = new Set<string>();
    const buildingMap = new Map(buildings.map((b) => [b.id, b]));

    for (const agent of agents) {
      seen.add(agent.id);

      let container = this.agentSprites.get(agent.id);
      if (!container) {
        container = this.createAgentSprite(agent.type);
        this.agentSprites.set(agent.id, container);
        this.agentLayer.addChild(container);
      }

      this.positionAgentSprite(container, agent, buildingMap);
    }

    // Remove stale
    for (const [id, container] of this.agentSprites) {
      if (!seen.has(id)) {
        this.agentLayer.removeChild(container);
        container.destroy({ children: true });
        this.agentSprites.delete(id);
      }
    }
  }

  private createAgentSprite(type: AgentType): PIXI.Container {
    const container = new PIXI.Container();
    const color = AGENT_COLORS[type] ?? 0xffffff;

    const g = new PIXI.Graphics();
    // Hexagonal shape (6 vertices)
    const r = 10;
    g.lineStyle(1.5, color, 0.9);
    g.beginFill(color, 0.35);
    const points: number[] = [];
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i - Math.PI / 6;
      points.push(r * Math.cos(angle), r * Math.sin(angle));
    }
    g.drawPolygon(points);
    g.endFill();

    // Center dot
    g.beginFill(color, 0.9);
    g.drawCircle(0, 0, 3);
    g.endFill();

    container.addChild(g);

    // Outer glow ring
    const glow = new PIXI.Graphics();
    glow.lineStyle(1, color, 0.3);
    glow.drawCircle(0, 0, 14);
    container.addChild(glow);

    return container;
  }

  private positionAgentSprite(
    container: PIXI.Container,
    agent: Agent,
    buildingMap: Map<string, Building>
  ): void {
    const currentPos = this.agentPositions.get(agent.id);

    let targetX: number;
    let targetY: number;

    const targetBuilding = agent.targetBuildingId
      ? buildingMap.get(agent.targetBuildingId)
      : agent.currentBuildingId
      ? buildingMap.get(agent.currentBuildingId)
      : null;

    if (targetBuilding) {
      const center = this.getBuildingCenter(targetBuilding);
      targetX = center.x;
      targetY = center.y;
    } else {
      // Default position based on agent type
      const idx = Array.from(this.agentSprites.keys()).indexOf(agent.id);
      targetX = 50 + idx * 60;
      targetY = 50;
    }

    if (!currentPos) {
      this.agentPositions.set(agent.id, { x: targetX, y: targetY });
      container.x = targetX;
      container.y = targetY;
    } else {
      // Smooth interpolation towards target
      const speed = 0.08;
      const newX = currentPos.x + (targetX - currentPos.x) * speed;
      const newY = currentPos.y + (targetY - currentPos.y) * speed;
      this.agentPositions.set(agent.id, { x: newX, y: newY });
      container.x = newX;
      container.y = newY;
    }

    // Visual feedback for status
    if (agent.status === 'acting') {
      container.alpha = 1.0;
      container.scale.set(1.2 + 0.1 * Math.sin(this.animationTime * 8));
    } else if (agent.status === 'analyzing') {
      container.alpha = 0.9;
      container.scale.set(1.0);
      container.rotation = this.animationTime * 0.5;
    } else if (agent.status === 'blocked') {
      container.alpha = 0.5 + 0.3 * Math.sin(this.animationTime * 5);
      container.scale.set(1.0);
    } else {
      container.alpha = 0.8;
      container.scale.set(1.0);
      container.rotation = 0;
    }
  }

  // ─── Overlay ────────────────────────────────────────────────────────────────

  private updateOverlay(state: SimulationState, mode: OverlayMode): void {
    this.overlayLayer.removeChildren();

    if (mode === 'none') return;

    const buildingMap = new Map(state.buildings.map((b) => [b.id, b]));

    switch (mode) {
      case 'dependency':
        this.drawDependencyOverlay(state.buildings, buildingMap);
        break;
      case 'congestion':
        this.drawCongestionOverlay(state.buildings);
        break;
      case 'trust':
        this.drawTrustOverlay(state.buildings);
        break;
      case 'staffing':
        this.drawStaffingOverlay(state.buildings);
        break;
      case 'outage':
        this.drawOutageOverlay(state.buildings);
        break;
      case 'orchestration':
        this.drawOrchestrationOverlay(state.workflows, buildingMap);
        break;
    }
  }

  private drawDependencyOverlay(
    buildings: Building[],
    buildingMap: Map<string, Building>
  ): void {
    for (const building of buildings) {
      for (const depId of building.dependencies) {
        const dep = buildingMap.get(depId);
        if (!dep) continue;

        const src = this.getBuildingCenter(building);
        const dst = this.getBuildingCenter(dep);

        const arrow = new PIXI.Graphics();
        arrow.lineStyle(2, 0x00d4ff, 0.7);
        arrow.moveTo(src.x, src.y);
        arrow.lineTo(dst.x, dst.y);

        // Arrowhead
        const dx = dst.x - src.x;
        const dy = dst.y - src.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const ux = dx / dist;
        const uy = dy / dist;
        const arrowSize = 10;
        arrow.beginFill(0x00d4ff, 0.7);
        arrow.moveTo(dst.x, dst.y);
        arrow.lineTo(
          dst.x - arrowSize * ux - arrowSize * 0.5 * uy,
          dst.y - arrowSize * uy + arrowSize * 0.5 * ux
        );
        arrow.lineTo(
          dst.x - arrowSize * ux + arrowSize * 0.5 * uy,
          dst.y - arrowSize * uy - arrowSize * 0.5 * ux
        );
        arrow.closePath();
        arrow.endFill();

        this.overlayLayer.addChild(arrow);
      }
    }
  }

  private drawCongestionOverlay(buildings: Building[]): void {
    for (const building of buildings) {
      const pos = this.getTilePos(building.pos.x, building.pos.y);
      const w = building.pos.w * TILE_SIZE;
      const h = building.pos.h * TILE_SIZE;

      // queueDepth as congestion measure
      const congestion = Math.min(1, building.queueDepth / 20);

      let color: number;
      if (congestion < 0.33) color = 0x44ff88;
      else if (congestion < 0.66) color = 0xffaa00;
      else color = 0xff4444;

      const overlay = new PIXI.Graphics();
      overlay.beginFill(color, 0.35 * congestion + 0.1);
      overlay.drawRoundedRect(pos.x, pos.y, w, h, 4);
      overlay.endFill();
      this.overlayLayer.addChild(overlay);

      // Label
      const text = new PIXI.Text(`Q:${building.queueDepth}`, {
        fontSize: 10,
        fill: color,
        fontWeight: 'bold',
      });
      text.x = pos.x + w / 2 - text.width / 2;
      text.y = pos.y + 4;
      this.overlayLayer.addChild(text);
    }
  }

  private drawTrustOverlay(buildings: Building[]): void {
    for (const building of buildings) {
      const pos = this.getTilePos(building.pos.x, building.pos.y);
      const w = building.pos.w * TILE_SIZE;
      const h = building.pos.h * TILE_SIZE;

      const trust = building.trustLevel / 100;

      const overlay = new PIXI.Graphics();
      overlay.beginFill(0x4488ff, 0.1 + 0.4 * trust);
      overlay.drawRoundedRect(pos.x, pos.y, w, h, 4);
      overlay.endFill();
      this.overlayLayer.addChild(overlay);

      const text = new PIXI.Text(`${Math.round(building.trustLevel)}%`, {
        fontSize: 10,
        fill: 0x88aaff,
        fontWeight: 'bold',
      });
      text.x = pos.x + w / 2 - text.width / 2;
      text.y = pos.y + 4;
      this.overlayLayer.addChild(text);
    }
  }

  private drawStaffingOverlay(buildings: Building[]): void {
    for (const building of buildings) {
      const pos = this.getTilePos(building.pos.x, building.pos.y);
      const w = building.pos.w * TILE_SIZE;
      const h = building.pos.h * TILE_SIZE;

      const staffing = building.staffingLevel / 100;
      const color = staffing > 0.7 ? 0x44ff88 : staffing > 0.4 ? 0xff8800 : 0xff4444;

      const overlay = new PIXI.Graphics();
      overlay.beginFill(color, 0.1 + 0.3 * staffing);
      overlay.drawRoundedRect(pos.x, pos.y, w, h, 4);
      overlay.endFill();
      this.overlayLayer.addChild(overlay);

      const text = new PIXI.Text(`${Math.round(building.staffingLevel)}%`, {
        fontSize: 10,
        fill: color,
        fontWeight: 'bold',
      });
      text.x = pos.x + w / 2 - text.width / 2;
      text.y = pos.y + 4;
      this.overlayLayer.addChild(text);
    }
  }

  private drawOutageOverlay(buildings: Building[]): void {
    for (const building of buildings) {
      if (building.status === 'operational') continue;

      const pos = this.getTilePos(building.pos.x, building.pos.y);
      const w = building.pos.w * TILE_SIZE;
      const h = building.pos.h * TILE_SIZE;
      const cx = pos.x + w / 2;
      const cy = pos.y + h / 2;

      const haloColor =
        building.status === 'offline'
          ? 0xff2222
          : building.status === 'critical'
          ? 0xff4444
          : 0xffaa00;
      const haloAlpha = 0.25 + 0.15 * Math.sin(this.animationTime * 4);
      const haloRadius = Math.max(w, h) * 0.8;

      const halo = new PIXI.Graphics();
      halo.beginFill(haloColor, haloAlpha);
      halo.drawCircle(cx, cy, haloRadius);
      halo.endFill();
      this.overlayLayer.addChild(halo);
    }
  }

  private drawOrchestrationOverlay(
    workflows: Workflow[],
    buildingMap: Map<string, Building>
  ): void {
    // Draw active routing lines for workflows
    for (const wf of workflows) {
      if (wf.status === 'flowing' || wf.status === 'rerouted') {
        const src = buildingMap.get(wf.sourceId);
        const dst = buildingMap.get(wf.destId);
        if (!src || !dst) continue;

        const srcCenter = this.getBuildingCenter(src);
        const dstCenter = this.getBuildingCenter(dst);

        const line = new PIXI.Graphics();
        const color = WORKFLOW_COLORS[wf.type] ?? 0xffffff;
        line.lineStyle(2, color, 0.3);
        line.moveTo(srcCenter.x, srcCenter.y);
        line.lineTo(dstCenter.x, dstCenter.y);
        this.overlayLayer.addChild(line);
      }
    }
  }

  // ─── Animation tick ─────────────────────────────────────────────────────────

  private tickAnimations(): void {
    if (!this.lastState) return;

    // Animate building glows for operational state
    for (const [id, container] of this.buildingGraphics) {
      const building = this.lastState.buildings.find((b) => b.id === id);
      if (!building) continue;

      const glow = container.getChildAt(0) as PIXI.Graphics | null;
      if (!glow) continue;

      if (building.status === 'operational') {
        // Pulsing glow alpha
        glow.alpha = 0.6 + 0.4 * Math.sin(this.animationTime * 2 + id.charCodeAt(0));
      } else if (building.status === 'critical') {
        // Flickering
        glow.alpha = Math.random() > 0.1 ? 1 : 0.3;
      } else if (building.status === 'degraded') {
        glow.alpha = 0.7 + 0.3 * Math.sin(this.animationTime * 3);
      }
    }

    // Re-draw connection lines with updated animation time
    if (this.lastState) {
      this.updateConnections(this.lastState.buildings);
    }
  }

  // ─── Utility ────────────────────────────────────────────────────────────────

  getBuildingCenter(building: Building): { x: number; y: number } {
    const pos = this.getTilePos(building.pos.x, building.pos.y);
    return {
      x: pos.x + (building.pos.w * TILE_SIZE) / 2,
      y: pos.y + (building.pos.h * TILE_SIZE) / 2,
    };
  }

  getTilePos(gridX: number, gridY: number): { x: number; y: number } {
    return {
      x: gridX * TILE_SIZE,
      y: gridY * TILE_SIZE,
    };
  }

  onBuildingClick(callback: (buildingId: string) => void): void {
    this.buildingClickCallback = callback;
  }

  onAgentClick(callback: (agentId: string) => void): void {
    this.agentClickCallback = callback;
  }

  destroy(): void {
    this.app.ticker.stop();
    this.app.destroy(false, { children: true, texture: true, baseTexture: true });
  }
}
