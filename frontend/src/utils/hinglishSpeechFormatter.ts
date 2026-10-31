/**
 * Formats colloquial voice transcripts (Hindi / Hinglish / raw speech)
 * into formal, structured campus incident reports.
 */
export function formatHinglishSpeechToCleanDraft(
  rawTranscript: string,
  currentTitle: string = '',
  building: string = ''
): string {
  const text = rawTranscript.trim().toLowerCase();

  // 1. AC / Cooling issues
  if (
    text.includes('ac kaam nahi') ||
    text.includes('ac band') ||
    text.includes('garmi lag rahi') ||
    text.includes('cooling nahi') ||
    text.includes('ac not working')
  ) {
    const loc = building ? `in ${building}` : 'in the designated area';
    return `The air conditioning system ${loc} is currently non-functional and not cooling. This is causing significant discomfort to students during ongoing study hours. Kindly inspect the cooling unit and restore functionality promptly.`;
  }

  // 2. Water / Cooler / Tap leakage
  if (
    text.includes('paani') ||
    text.includes('water cooler') ||
    text.includes('tap') ||
    text.includes('leak') ||
    text.includes('pani gir') ||
    text.includes('नल')
  ) {
    const loc = building ? `at ${building}` : 'on-site';
    return `The drinking water dispenser/tap ${loc} is leaking water continuously, causing water accumulation on the corridor floor. This creates a slippery hazard for students passing by. Immediate maintenance is requested to fix the valve/pipe.`;
  }

  // 3. Electric spark / Wire / Switchboard hazard
  if (
    text.includes('spark') ||
    text.includes('bijli') ||
    text.includes('shock') ||
    text.includes('wire') ||
    text.includes('smoke') ||
    text.includes('jal gaya')
  ) {
    const loc = building ? `near ${building}` : 'in the facility';
    return `Sparks and burning odor observed near the electric switch panel ${loc}. This represents a severe safety hazard to students in the vicinity. Immediate technician inspection and power isolation required.`;
  }

  // 4. Projector / Classroom display / HDMI
  if (
    text.includes('projector') ||
    text.includes('display nahi') ||
    text.includes('screen black') ||
    text.includes('hdmi') ||
    text.includes('chal nahi raha')
  ) {
    const loc = building ? `in ${building}` : 'in the classroom';
    return `The classroom display projector ${loc} is unable to receive video signal via HDMI/VGA cable. Lectures are being disrupted due to the display failure. Kindly arrange AV repair or cable replacement.`;
  }

  // 5. Light / Tube light fused
  if (
    text.includes('light nahi') ||
    text.includes('tube light') ||
    text.includes('andhera') ||
    text.includes('fused') ||
    text.includes('bulb')
  ) {
    const loc = building ? `in ${building}` : 'in the room';
    return `The primary ceiling lights ${loc} are completely non-functional/fused, resulting in poor illumination during evening study hours. Please arrange for replacement tube lights.`;
  }

  // 6. Furniture / Chair / Bench broken
  if (
    text.includes('bench') ||
    text.includes('chair') ||
    text.includes('desk') ||
    text.includes('toota') ||
    text.includes('broken')
  ) {
    const loc = building ? `at ${building}` : 'in the room';
    return `The classroom/facility seating furniture ${loc} is structurally damaged with sharp edges exposed. It is unusable and poses an injury risk. Kindly arrange carpentry repair or replacement.`;
  }

  // Generic polishing fallback: Capitalize and structure properly
  const cleaned = rawTranscript.charAt(0).toUpperCase() + rawTranscript.slice(1);
  return `${cleaned}. Reported on-site by student. Immediate inspection requested by campus facilities team.`;
}

