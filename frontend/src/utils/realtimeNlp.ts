/**
 * Real-time Client-side NLP Intelligence Simulation for CampusVoice
 * Evaluates complaint title & description dynamically on each keystroke.
 */

export interface NlpAnalysisResult {
  category: 'Sanitation & Plumbing' | 'Electrical & Hardware' | 'Academics & Classroom' | 'General Infrastructure';
  categoryColor: string;
  categoryIcon: string;
  priority: 'Critical (P1)' | 'Medium (P2)' | 'Normal (P3)';
  priorityLevel: 'P1' | 'P2' | 'P3';
  priorityColor: string;
  priorityBg: string;
  duplicateHint: string | null;
  detectedKeywords: string[];
}

// 1. Priority keyword dictionaries
const P1_CRITICAL_KEYWORDS = [
  'fire', 'spark', 'sparks', 'sparking', 'shock', 'shocks', 'broken glass',
  'danger', 'dangerous', 'blast', 'smoke', 'hazard', 'hazardous', 'live wire',
  'exposed wire', 'short circuit', 'electrocution', 'burning', 'emergency',
  'gas leak', 'structural collapse'
];

const P2_MEDIUM_KEYWORDS = [
  'leak', 'leaks', 'leaking', 'leakage', 'broken', 'urgent', 'overflow',
  'overflowing', 'stuck', 'not working', 'damage', 'damaged', 'cracked',
  'faulty', 'failure', 'dripping', 'choked', 'blocked', 'cut off', 'shuts down'
];

// 2. Category keyword dictionaries
const SANITATION_KEYWORDS = [
  'water', 'cooler', 'drinking water', 'leak', 'leaking', 'washroom', 'restroom',
  'toilet', 'tap', 'basin', 'sink', 'drain', 'drainage', 'flush', 'plumbing',
  'pipe', 'sewage', 'sewer', 'odor', 'smell', 'dirty', 'hygiene', 'garbage',
  'waste', 'sanitation', 'restrooms', 'clogged', 'puddle'
];

const ELECTRICAL_KEYWORDS = [
  'spark', 'sparking', 'wire', 'wires', 'socket', 'switch', 'current', 'shock',
  'electricity', 'power', 'blackout', 'outage', 'light', 'lights', 'tube light',
  'bulb', 'fan', 'ac', 'air conditioner', 'hvac', 'fuse', 'circuit', 'voltage',
  'board', 'conduit', 'breaker', 'short circuit', 'appliance'
];

const ACADEMICS_KEYWORDS = [
  'projector', 'screen', 'podium', 'mic', 'microphone', 'audio', 'speaker',
  'lecture', 'lecture hall', 'classroom', 'blackboard', 'whiteboard', 'attendance',
  'lab', 'physics', 'chemistry', 'computer lab', 'timetable', 'clash', 'overlap',
  'professor', 'exam', 'examination', 'hall ticket', 'marks', 'grade', 'portal',
  'syllabus', 'tutorial', 'class', 'presentation'
];

const INFRASTRUCTURE_KEYWORDS = [
  'window', 'glass', 'door', 'lock', 'handle', 'bench', 'benches', 'desk',
  'desks', 'chair', 'chairs', 'table', 'lift', 'elevator', 'wall', 'walls',
  'ceiling', 'roof', 'stairs', 'staircase', 'floor', 'tile', 'tiles', 'pavement',
  'road', 'pathway', 'gate', 'railing', 'paint', 'plaster'
];

// 3. Known issue duplicate patterns
interface DuplicatePattern {
  triggers: string[];
  message: string;
}

const DUPLICATE_PATTERNS: DuplicatePattern[] = [
  {
    triggers: ['water cooler', 'cooler leak', 'cooler leaking', 'drinking water leak', 'water filter'],
    message: '12 others have reported a similar issue. Your report will be automatically grouped.',
  },
  {
    triggers: ['sparking socket', 'socket spark', 'socket sparking', 'wall socket spark', 'live wire', 'exposed wire'],
    message: '4 other students reported electrical hazards at this site. Grouping with active master ticket.',
  },
  {
    triggers: ['projector flickering', 'projector', 'projector display', 'overhead projector', 'lh projector'],
    message: '3 similar lecture hall projector reports found. Grouping enabled.',
  },
  {
    triggers: ['wifi', 'wi-fi', 'eduroam', 'internet down', 'slow internet', 'no internet', 'wifi not working'],
    message: '8 campus residents reported network drops here. Your report will reinforce this incident.',
  },
  {
    triggers: ['washroom leak', 'toilet leak', 'tap leaking', 'bathroom water', 'restroom pipe'],
    message: '6 similar sanitation tickets logged today. Automatic grouping active.',
  },
  {
    triggers: ['lift stuck', 'elevator not working', 'lift stopped', 'elevator stuck'],
    message: '5 other students reported this elevator fault. Auto-grouping with maintenance queue.',
  },
];

export function analyzeComplaintText(title: string, description: string): NlpAnalysisResult {
  const combined = `${title} ${description}`.toLowerCase().trim();
  const detectedKeywords: string[] = [];

  // 1. Dynamic Priority Tagging
  let priority: 'Critical (P1)' | 'Medium (P2)' | 'Normal (P3)' = 'Normal (P3)';
  let priorityLevel: 'P1' | 'P2' | 'P3' = 'P3';
  let priorityColor = '#16a34a'; // Green
  let priorityBg = '#f0fdf4';

  const hasP1 = P1_CRITICAL_KEYWORDS.some((kw) => {
    if (combined.includes(kw)) {
      detectedKeywords.push(kw);
      return true;
    }
    return false;
  });

  if (hasP1) {
    priority = 'Critical (P1)';
    priorityLevel = 'P1';
    priorityColor = '#dc2626'; // Red
    priorityBg = '#fef2f2';
  } else {
    const hasP2 = P2_MEDIUM_KEYWORDS.some((kw) => {
      if (combined.includes(kw)) {
        detectedKeywords.push(kw);
        return true;
      }
      return false;
    });

    if (hasP2) {
      priority = 'Medium (P2)';
      priorityLevel = 'P2';
      priorityColor = '#d97706'; // Amber
      priorityBg = '#fffbeb';
    }
  }

  // 2. Auto-Categorization scoring
  let scoreSanitation = 0;
  let scoreElectrical = 0;
  let scoreAcademics = 0;
  let scoreInfra = 0;

  SANITATION_KEYWORDS.forEach((kw) => {
    if (combined.includes(kw)) {
      scoreSanitation += kw.length > 5 ? 2 : 1;
      if (!detectedKeywords.includes(kw)) detectedKeywords.push(kw);
    }
  });

  ELECTRICAL_KEYWORDS.forEach((kw) => {
    if (combined.includes(kw)) {
      scoreElectrical += kw.length > 5 ? 2 : 1;
      if (!detectedKeywords.includes(kw)) detectedKeywords.push(kw);
    }
  });

  ACADEMICS_KEYWORDS.forEach((kw) => {
    if (combined.includes(kw)) {
      scoreAcademics += kw.length > 5 ? 2 : 1;
      if (!detectedKeywords.includes(kw)) detectedKeywords.push(kw);
    }
  });

  INFRASTRUCTURE_KEYWORDS.forEach((kw) => {
    if (combined.includes(kw)) {
      scoreInfra += kw.length > 5 ? 2 : 1;
      if (!detectedKeywords.includes(kw)) detectedKeywords.push(kw);
    }
  });

  let category: 'Sanitation & Plumbing' | 'Electrical & Hardware' | 'Academics & Classroom' | 'General Infrastructure' =
    'General Infrastructure';
  let categoryColor = '#2563eb';
  let categoryIcon = 'bi-building-fill';

  const maxScore = Math.max(scoreSanitation, scoreElectrical, scoreAcademics, scoreInfra);

  if (maxScore > 0) {
    if (maxScore === scoreSanitation) {
      category = 'Sanitation & Plumbing';
      categoryColor = '#0284c7';
      categoryIcon = 'bi-droplet-half';
    } else if (maxScore === scoreElectrical) {
      category = 'Electrical & Hardware';
      categoryColor = '#ea580c';
      categoryIcon = 'bi-lightning-charge-fill';
    } else if (maxScore === scoreAcademics) {
      category = 'Academics & Classroom';
      categoryColor = '#7c3aed';
      categoryIcon = 'bi-mortarboard-fill';
    } else {
      category = 'General Infrastructure';
      categoryColor = '#2563eb';
      categoryIcon = 'bi-building-fill';
    }
  }

  // 3. Duplicate Matching Alert
  let duplicateHint: string | null = null;
  for (const pattern of DUPLICATE_PATTERNS) {
    if (pattern.triggers.some((trigger) => combined.includes(trigger))) {
      duplicateHint = pattern.message;
      break;
    }
  }

  // Generic duplicate alert if high overlap with known frequent issues
  if (!duplicateHint && combined.length > 15 && (combined.includes('leak') || combined.includes('broken socket') || combined.includes('projector'))) {
    duplicateHint = '12 others have reported a similar issue. Your report will be automatically grouped.';
  }

  return {
    category,
    categoryColor,
    categoryIcon,
    priority,
    priorityLevel,
    priorityColor,
    priorityBg,
    duplicateHint,
    detectedKeywords: Array.from(new Set(detectedKeywords)).slice(0, 5),
  };
}

