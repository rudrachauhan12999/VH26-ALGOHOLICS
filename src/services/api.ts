/**
 * SARVA-SENSE FRONTEND SERVICE ABSTRACTIONS
 * 
 * NOTE: These are frontend service abstractions using mock data and simulated latencies.
 * When a real backend is implemented in the future, these methods can easily be pointed
 * to real FastAPI/Node endpoints without changing the UI components.
 */

import {
  MOCK_ANSWER_E101_HP200X,
  MOCK_ANSWER_OVERHEATING_HP200X,
  MOCK_AMBIGUITY_E101,
  MOCK_INSUFFICIENT_INFO,
  MOCK_HMI_ANALYSIS,
  MOCK_OCR_PAGE,
  MOCK_MACHINES,
  MOCK_MANUALS,
} from '../data/mockData';
import { StructuredAnswer, HMIScreenshotAnalysis, OCRPageAnalysis, Machine, Manual, QueryType } from '../types';

export interface DiagnoseQueryOptions {
  query: string;
  machineId?: string;
  queryType?: QueryType;
  onProgress?: (stage: string) => void;
}

export interface DiagnoseQueryResult {
  type: 'STRUCTURED_ANSWER' | 'AMBIGUITY' | 'INSUFFICIENT_INFO';
  answer?: StructuredAnswer;
  ambiguity?: typeof MOCK_AMBIGUITY_E101;
  insufficient?: typeof MOCK_INSUFFICIENT_INFO;
}

export const troubleshootingService = {
  async diagnose(options: DiagnoseQueryOptions): Promise<DiagnoseQueryResult> {
    const { query, machineId, onProgress } = options;
    const clean = query.trim().toUpperCase();

    // Multi-stage simulated RAG pipeline steps
    const stages = [
      'Understanding query intent & technical terms...',
      'Identifying equipment context & model schema...',
      'Searching indexing partitions across 4 machine manuals...',
      'Ranking evidence vectors & matching alarm codes...',
      'Verifying claims against OEM maintenance procedures...',
      'Synthesizing safety-verified troubleshooting actions...',
    ];

    for (let i = 0; i < stages.length; i++) {
      if (onProgress) onProgress(stages[i]);
      await new Promise((resolve) => setTimeout(resolve, 280));
    }

    // SCENARIO 3: Ambiguous E101 without machine context
    if ((clean === 'E101' || clean.includes('E101')) && (!machineId || machineId === 'any')) {
      return {
        type: 'AMBIGUITY',
        ambiguity: MOCK_AMBIGUITY_E101,
      };
    }

    // SCENARIO 4: Insufficient Information (sound/noise or unknown symptom without manual support)
    if (
      clean.includes('NOISE') ||
      clean.includes('HIGH-PITCHED') ||
      clean.includes('STRANGE SOUND') ||
      clean.includes('VIBRATION') ||
      clean.includes('UNKNOWN')
    ) {
      return {
        type: 'INSUFFICIENT_INFO',
        insufficient: MOCK_INSUFFICIENT_INFO,
      };
    }

    // SCENARIO 2: Overheating
    if (clean.includes('OVERHEAT') || clean.includes('TEMP') || clean.includes('HEAT') || clean.includes('HOT')) {
      return {
        type: 'STRUCTURED_ANSWER',
        answer: MOCK_ANSWER_OVERHEATING_HP200X,
      };
    }

    // SCENARIO 1 (DEFAULT): E101 on HP-200X or standard fault
    return {
      type: 'STRUCTURED_ANSWER',
      answer: MOCK_ANSWER_E101_HP200X,
    };
  },
};

export const manualService = {
  async getManuals(): Promise<Manual[]> {
    await new Promise((r) => setTimeout(r, 100));
    return MOCK_MANUALS;
  },

  async uploadManual(file: File, onProgress?: (percent: number, stage: string) => void): Promise<Manual> {
    const stages = [
      { pct: 15, msg: 'Uploading PDF to encrypted local storage...' },
      { pct: 35, msg: 'Decompressing PDF raster layers & font maps...' },
      { pct: 60, msg: 'Extracting page index & technical diagrams...' },
      { pct: 85, msg: 'Running neural OCR table & vector extraction...' },
      { pct: 100, msg: 'Manual indexed and ready for grounded retrieval.' },
    ];

    for (const step of stages) {
      if (onProgress) onProgress(step.pct, step.msg);
      await new Promise((r) => setTimeout(r, 380));
    }

    const newManual: Manual = {
      id: 'man-' + Date.now(),
      title: file.name.replace('.pdf', '') || 'Uploaded Industrial Manual',
      machineId: 'hp-200x',
      machineName: 'Hydraulic Press HP-200X',
      model: 'HP-200X',
      pages: Math.floor(Math.random() * 200) + 85,
      fileSize: (file.size / (1024 * 1024)).toFixed(1) + ' MB',
      ocrStatus: 'Completed',
      status: 'Indexed',
      uploadedDate: new Date().toISOString().split('T')[0],
      version: 'Rev 1.0 (User Uploaded)',
      tabColor: '#38BDF8',
    };

    return newManual;
  },
};

export const ocrService = {
  async processScannedPage(pageNumber: number, onProgress?: (stage: string) => void): Promise<OCRPageAnalysis> {
    const stages = [
      'Scanning high-resolution page raster...',
      'Binarizing image & removing scanner skew...',
      'Detecting multi-column text geometry & tables...',
      'Recognizing technical error codes & part numbers...',
      'Cross-referencing alarm codes against OEM database...',
    ];

    for (const stage of stages) {
      if (onProgress) onProgress(stage);
      await new Promise((r) => setTimeout(r, 260));
    }

    return {
      ...MOCK_OCR_PAGE,
      pageNumber,
    };
  },
};

export const visionService = {
  async analyzeScreenshot(imageSrc: string, onProgress?: (stage: string) => void): Promise<HMIScreenshotAnalysis> {
    const stages = [
      'Pre-processing HMI screen capture...',
      'Detecting display bezel & perspective alignment...',
      'Segmenting alarm banners, gauge widgets, and numeric readouts...',
      'Running optical character recognition on fault panels...',
      'Synthesizing machine state and safety interlock condition...',
    ];

    for (const stage of stages) {
      if (onProgress) onProgress(stage);
      await new Promise((r) => setTimeout(r, 300));
    }

    return MOCK_HMI_ANALYSIS;
  },
};

export const machineService = {
  async getMachines(): Promise<Machine[]> {
    await new Promise((r) => setTimeout(r, 80));
    return MOCK_MACHINES;
  },
};
