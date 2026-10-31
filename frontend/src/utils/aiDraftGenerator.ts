/**
 * AI Auto-Draft Assistant for Campus Complaints & Maintenance Requests.
 * Dynamically synthesizes structured, high-clarity descriptions from title and location keywords.
 */

export function generateAiDraftDescription(
  title: string,
  building: string,
  room?: string
): string {
  const cleanTitle = (title || '').trim().toLowerCase();
  const locationDesc = room && room.trim() ? `${room.trim()}, ${building}` : building;

  // 1. Electrical / Sparking / Switchboard / Fire Hazard
  if (
    cleanTitle.includes('spark') ||
    cleanTitle.includes('switchboard') ||
    cleanTitle.includes('socket') ||
    cleanTitle.includes('shock') ||
    cleanTitle.includes('short circuit') ||
    cleanTitle.includes('smoke') ||
    cleanTitle.includes('fire') ||
    cleanTitle.includes('exposed wire') ||
    cleanTitle.includes('bijli')
  ) {
    return `Sparks and a burning odor observed near the electric switch panel in ${locationDesc}. Potential safety risk to students in the area. Immediate technician inspection required.`;
  }

  // 2. Water Cooler / Leaks / Tap / Dispenser
  if (
    cleanTitle.includes('water cooler') ||
    cleanTitle.includes('cooler') ||
    cleanTitle.includes('dispenser') ||
    cleanTitle.includes('drinking water')
  ) {
    if (cleanTitle.includes('leak') || cleanTitle.includes('pool') || cleanTitle.includes('overflow')) {
      return `Drinking water dispenser in ${locationDesc} is continuously leaking water all over the floor. This creates a slip-and-fall hazard in the walkway. Urgent plumbing maintenance requested.`;
    }
    return `The drinking water dispenser is currently non-functional and not chilling water in ${locationDesc}. This is causing significant inconvenience to students between classes. Please inspect the cooling unit and water supply filters.`;
  }

  // 3. Projector / Display / HDMI / Classroom AV
  if (
    cleanTitle.includes('projector') ||
    cleanTitle.includes('hdmi') ||
    cleanTitle.includes('display') ||
    cleanTitle.includes('screen') ||
    cleanTitle.includes('mic') ||
    cleanTitle.includes('speaker') ||
    cleanTitle.includes('audio')
  ) {
    if (cleanTitle.includes('hdmi') || cleanTitle.includes('cable') || cleanTitle.includes('pin') || cleanTitle.includes('wire')) {
      return `The display connector cable/HDMI interface in ${locationDesc} is damaged and cannot establish video output. Instructors and students are unable to project course slides. Kindly replace the cable.`;
    }
    return `The classroom display/hardware is malfunctioning during ongoing lecture hours in ${locationDesc}. Kindly arrange repair or replacement at the earliest.`;
  }

  // 4. Broken Furniture / Classroom / Study Area
  if (
    cleanTitle.includes('bench') ||
    cleanTitle.includes('chair') ||
    cleanTitle.includes('desk') ||
    cleanTitle.includes('table') ||
    cleanTitle.includes('furniture')
  ) {
    return `The seating/desk furniture in ${locationDesc} is damaged with broken joints and sharp edges. This poses an injury risk and prevents student seating during sessions. Requesting replacement.`;
  }

  // 5. Infrastructure: Doors / Windows / Glass / Elevator
  if (cleanTitle.includes('elevator') || cleanTitle.includes('lift')) {
    return `The elevator in ${locationDesc} is unresponsive and experiencing erratic door operation. Students risk getting trapped between floors. Urgent inspection required.`;
  }

  if (cleanTitle.includes('glass') || cleanTitle.includes('window') || cleanTitle.includes('door') || cleanTitle.includes('lock')) {
    return `Damaged fittings and broken fixtures observed in ${locationDesc}. Poses an immediate security and safety concern for students. Please deploy facility repairs promptly.`;
  }

  // 6. Restroom / Sanitation / Drainage
  if (
    cleanTitle.includes('washroom') ||
    cleanTitle.includes('toilet') ||
    cleanTitle.includes('restroom') ||
    cleanTitle.includes('tap') ||
    cleanTitle.includes('drain') ||
    cleanTitle.includes('sewage') ||
    cleanTitle.includes('smell') ||
    cleanTitle.includes('odor') ||
    cleanTitle.includes('flush')
  ) {
    return `Sanitary fittings in ${locationDesc} are malfunctioning with poor drainage and persistent water leakage. Comprehensive maintenance and sanitation servicing needed urgently.`;
  }

  // 7. IT / Connectivity / Wi-Fi
  if (
    cleanTitle.includes('wifi') ||
    cleanTitle.includes('wi-fi') ||
    cleanTitle.includes('internet') ||
    cleanTitle.includes('network') ||
    cleanTitle.includes('slow')
  ) {
    return `Severe Wi-Fi connectivity degradation and intermittent access drops reported in ${locationDesc}. Students and faculty cannot reach academic portals. Kindly reset access points and check bandwidth.`;
  }

  // 8. Hinglish Support
  if (cleanTitle.includes('paani') || cleanTitle.includes('pani') || cleanTitle.includes('nal')) {
    return `Drinking water supply and dispenser facility in ${locationDesc} is non-operational. Water is not chilling properly and causing daily inconvenience to residents. Kindly repair the cooling unit.`;
  }

  // 9. Intelligent Default Fallback
  return `An ongoing operational malfunction has been observed regarding "${title.trim()}" in ${locationDesc}. This issue causes regular disruptions to academic and student activities. Kindly inspect and resolve at the earliest convenience.`;
}

