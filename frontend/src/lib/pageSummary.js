import { INCIDENT_KIND } from "./vocab.js";

const PAGES = {
  "/": ["dashboard", "Dashboard", "สรุปสถานะระบบ", "See how the system is doing and which incidents need attention.", "ดูสถานะระบบและเหตุการณ์ที่ต้องติดตาม"],
  "/overview": ["technical_overview", "Technical overview", "ภาพรวมเชิงเทคนิค", "See detailed monitoring, investigation and recovery metrics.", "ดูข้อมูลการเฝ้าดู การหาสาเหตุ และการแก้ปัญหาโดยละเอียด"],
  "/problems": ["incident_list", "Incidents", "เหตุการณ์", "See incidents waiting for a decision, in progress or recently closed.", "ดูเหตุการณ์ที่รอการตัดสินใจ กำลังดำเนินการ และสิ้นสุดแล้ว"],
  "/problems/:id": ["incident_detail", "Incident details", "รายละเอียดเหตุการณ์", "Follow the incident from detection through investigation and any proposed fix.", "ติดตามเหตุการณ์ตั้งแต่ตรวจพบ หาสาเหตุ ไปจนถึงวิธีแก้ที่เสนอ"],
  "/services": ["service_list", "Services", "บริการ", "See the apps and devices the system knows about.", "ดูแอปและอุปกรณ์ที่ระบบรู้จัก"],
  "/services/:name": ["service_detail", "Service details", "รายละเอียดบริการ", "Check whether this service is working and whether any incidents are linked to it.", "ดูว่าบริการนี้ทำงานเป็นอย่างไรและมีเหตุการณ์ที่เกี่ยวข้องหรือไม่"],
  "/computers": ["host_list", "Hosts", "เครื่อง", "See the computers connected for monitoring.", "ดูเครื่องที่เชื่อมต่อให้ระบบเฝ้าดู"],
  "/computers/:name": ["host_detail", "Host details", "รายละเอียดเครื่อง", "See this computer’s health and the services running on it.", "ดูสถานะเครื่องนี้และบริการที่ทำงานอยู่บนเครื่อง"],
  "/map": ["service_map", "Service map", "แผนผังบริการ", "Follow how requests travel between services and see where trouble is reported.", "ดูเส้นทางการส่งคำขอระหว่างบริการและจุดที่มีรายงานปัญหา"],
  "/network": ["fleet_map", "Fleet map", "แผนที่เครื่องและอุปกรณ์", "See which computers and devices are known and which are monitored.", "ดูเครื่องและอุปกรณ์ที่ระบบรู้จัก พร้อมสถานะการเฝ้าดู"],
  "/network/list": ["fleet_list", "Fleet list", "รายการเครื่องและอุปกรณ์", "Browse discovered devices grouped by network, service or owner.", "ดูอุปกรณ์ที่ตรวจพบ โดยจัดตามเครือข่าย บริการ หรือเจ้าของ"],
  "/network/3d": ["fleet_3d", "Fleet in 3D", "แผนที่เครื่องและอุปกรณ์ 3 มิติ", "Explore how networks, computers and services are connected.", "สำรวจว่าเครือข่าย เครื่อง และบริการเชื่อมถึงกันอย่างไร"],
  "/cloud": ["cloud_accounts", "Cloud accounts", "บัญชีคลาวด์", "See machines from connected cloud accounts and check their monitoring coverage.", "ดูเครื่องจากบัญชีคลาวด์ที่เชื่อมต่อและสถานะการเฝ้าดู"],
  "/insights": ["insights", "Insights", "ข้อสังเกตจากข้อมูล", "See patterns the platform found and areas worth checking.", "ดูแนวโน้มที่ระบบพบและจุดที่ควรตรวจสอบ"],
  "/connect": ["connect", "Connect", "เชื่อมต่อ", "Choose a computer, service, website or cloud account to monitor.", "เลือกเครื่อง บริการ เว็บไซต์ หรือบัญชีคลาวด์ที่ต้องการเฝ้าดู"],
  "/connect/computer": ["connect_computer", "Connect a computer", "เชื่อมต่อเครื่อง", "Set up a computer so it can report its health to the platform.", "ตั้งค่าเครื่องให้ส่งข้อมูลสถานะมายังระบบ"],
  "/connect/service": ["connect_service", "Connect a service", "เชื่อมต่อบริการ", "Set up an app to send monitoring data, then check that it arrives.", "ตั้งค่าแอปให้ส่งข้อมูลสำหรับเฝ้าดู แล้วตรวจว่าระบบได้รับข้อมูล"],
  "/connect/website": ["connect_website", "Watch a website", "เฝ้าดูเว็บไซต์", "Set up regular checks so you can see whether a website responds.", "ตั้งค่าการตรวจเป็นระยะเพื่อดูว่าเว็บไซต์ตอบสนองหรือไม่"],
  "/skills": ["ai_skills", "AI skills", "ทักษะ AI", "See the instructions the AI can use when it investigates an incident.", "ดูชุดคำแนะนำที่ AI ใช้ระหว่างหาสาเหตุของเหตุการณ์"],
  "/playbooks": ["playbooks", "Playbooks", "กติกาการรับมือ", "See the rules for who gets an incident and when it is escalated.", "ดูกติกาว่าใครรับผิดชอบเหตุการณ์และเมื่อใดจึงต้องส่งต่อ"],
  "/runbooks": ["runbooks", "Runbooks", "คู่มือแก้ไข", "See the procedures available for recurring problems.", "ดูขั้นตอนแก้ไขที่นำกลับมาใช้เมื่อเกิดปัญหาเดิม"],
  "/notifications": ["notifications", "Notifications", "การแจ้งเตือน", "Review the recent messages the system tried to send.", "ดูรายการแจ้งเตือนล่าสุดที่ระบบพยายามส่ง"],
  "/deployments": ["deployments", "Deployments", "การออกรุ่น", "See recent software releases that were recorded in the platform.", "ดูการออกรุ่นล่าสุดที่บันทึกไว้ในระบบ"],
  "/scenarios": ["demo_scenarios", "Demo scenarios", "สถานการณ์สาธิต", "See available examples of how monitoring and incident response work.", "ดูตัวอย่างการเฝ้าดูและการรับมือเมื่อเกิดปัญหา"],
  "/pricing": ["pricing", "Pricing", "ราคา", "Compare the plans shown on this page.", "เปรียบเทียบแผนบริการที่แสดงในหน้านี้"],
  "/design": ["design_system", "Design system", "ระบบออกแบบ", "Browse examples of the colors, components and styles used in the app.", "ดูตัวอย่างสี องค์ประกอบ และรูปแบบที่ใช้ในแอป"],
  "/settings": ["settings", "Settings", "การตั้งค่า", "See how monitoring, automatic investigation and notifications are configured.", "ดูการตั้งค่าการเฝ้าดู การหาสาเหตุอัตโนมัติ และการแจ้งเตือน"],
  "/access": ["access", "Access", "สิทธิ์การเข้าถึง", "Manage who can sign in and what people can do in the workspace.", "จัดการว่าใครเข้าสู่ระบบได้และแต่ละคนมีสิทธิ์ทำอะไร"],
};
const NOT_FOUND = ["page_not_found", "Page unavailable", "ไม่พบหน้า", "The requested page could not be found.", "ไม่พบหน้าที่เปิดอยู่"];

export function pageContext(path, t) {
  const [id, en, th, purpose, purposeTh] = Object.hasOwn(PAGES, path) ? PAGES[path] : NOT_FOUND;
  return { id, title: t(en, th), purpose: t(purpose, purposeTh) };
}

const COUNTS = {
  open_incidents: ["Open incidents", "เหตุการณ์ที่ยังเปิดอยู่"],
  awaiting_approval: ["Fixes awaiting approval", "วิธีแก้ที่รออนุมัติ"],
  ai_investigations: ["AI investigating", "AI กำลังหาสาเหตุ"],
  fixes_in_progress: ["Applying or checking a fix", "กำลังแก้ไขหรือตรวจผล"],
  failed_fixes: ["Fixes that did not succeed", "แก้ไขไม่สำเร็จ"],
  recent_closed_incidents: ["Recently closed incidents shown", "เหตุการณ์ที่เพิ่งสิ้นสุดในรายการ"],
  monitored_services: ["Monitored services", "บริการที่เฝ้าดู"],
  services_with_issues: ["Services with issues", "บริการที่มีปัญหา"],
  monitored_hosts: ["Monitored computers", "เครื่องที่เฝ้าดู"],
  hosts_with_issues: ["Computers with issues", "เครื่องที่มีปัญหา"],
  resources_without_data: ["Services or computers without data", "บริการหรือเครื่องที่ขาดข้อมูล"],
  affected_services: ["Affected services", "บริการที่ได้รับผลกระทบ"],
  proposed_fixes: ["Proposed fixes", "วิธีแก้ที่เสนอ"],
  applications: ["Applications", "แอป"],
  network_devices: ["Network devices", "อุปกรณ์เครือข่าย"],
  discovered_services: ["Discovered services", "บริการที่ตรวจพบ"],
  map_connections: ["Connections on the map", "การเชื่อมต่อในแผนผัง"],
  known_machines: ["Known computers and devices", "เครื่องและอุปกรณ์ที่ระบบรู้จัก"],
  networks: ["Networks", "เครือข่าย"],
  cloud_accounts: ["Connected cloud accounts", "บัญชีคลาวด์ที่เชื่อมต่อ"],
  findings: ["Findings", "ข้อสังเกตจากข้อมูล"],
  available_skills: ["Listed AI skills", "ทักษะ AI ในรายการ"],
  enabled_runbooks: ["Enabled runbooks", "คู่มือแก้ไขที่เปิดใช้"],
  enabled_playbooks: ["Enabled playbooks", "กติกาการรับมือที่เปิดใช้"],
  recent_notifications: ["Recent notifications shown", "การแจ้งเตือนล่าสุดในรายการ"],
  recent_deployments: ["Recent releases shown", "การออกรุ่นล่าสุดในรายการ"],
  available_scenarios: ["Available demo scenarios", "สถานการณ์สาธิตที่เลือกได้"],
};

const STATES = {
  detector_active: ["Monitoring is active", "กำลังเฝ้าดูระบบ"],
  detector_unconfirmed: ["No recent check confirmed", "ยังไม่พบผลตรวจล่าสุด"],
  stale_data: ["The latest refresh failed", "อัปเดตล่าสุดไม่สำเร็จ"],
  incident_open: ["Incident detected", "ตรวจพบเหตุการณ์"],
  incident_analyzing: ["AI is investigating", "AI กำลังหาสาเหตุ"],
  incident_awaiting_approval: ["Waiting for the owner to review", "รอเจ้าของตรวจวิธีแก้"],
  incident_remediating: ["Applying the approved fix", "กำลังใช้วิธีแก้ที่อนุมัติแล้ว"],
  incident_verifying: ["Checking whether the fix worked", "กำลังตรวจผลการแก้ไข"],
  incident_resolved: ["Resolved", "แก้ไขแล้ว"],
  incident_rejected: ["Proposed fix declined", "ข้อเสนอแก้ไขถูกปฏิเสธ"],
  incident_closed: ["Incident closed", "ปิดเหตุการณ์แล้ว"],
  incident_remediation_failed: ["Fix did not succeed", "แก้ไขไม่สำเร็จ"],
  health_healthy: ["Latest health check looks good", "ผลตรวจล่าสุดอยู่ในเกณฑ์ปกติ"],
  health_problem: ["A problem has been reported", "มีรายงานปัญหา"],
  health_down: ["Currently unavailable", "ขณะนี้ไม่พร้อมใช้งาน"],
  health_offline: ["Currently offline", "ขณะนี้ออฟไลน์"],
  health_no_data: ["Waiting for monitoring data", "รอข้อมูลจากระบบเฝ้าดู"],
  test_sending: ["Sending a test request", "กำลังส่งคำขอทดสอบ"],
  test_tracing: ["Waiting for the test results", "กำลังรอผลทดสอบ"],
  test_playing: ["Showing the test request path", "กำลังแสดงเส้นทางของคำขอทดสอบ"],
  test_error: ["The test did not complete", "การทดสอบไม่สำเร็จ"],
  connecting: ["Connecting to monitoring", "กำลังเชื่อมต่อระบบเฝ้าดู"],
  connection_failed: ["The connection did not complete", "เชื่อมต่อไม่สำเร็จ"],
  waiting_for_data: ["Waiting for the first data", "รอข้อมูลชุดแรก"],
  sending_data: ["Monitoring data is coming in", "เริ่มได้รับข้อมูลสำหรับเฝ้าดูแล้ว"],
  check_successful: ["The latest website check succeeded", "ตรวจเว็บไซต์ครั้งล่าสุดสำเร็จ"],
  check_failed: ["The latest website check failed", "ตรวจเว็บไซต์ครั้งล่าสุดไม่สำเร็จ"],
  discovery_requested: ["Refreshing the device list", "กำลังขอข้อมูลอุปกรณ์รอบใหม่"],
  demo_starting: ["Starting a demo", "กำลังเริ่มสถานการณ์สาธิต"],
  auto_investigation_on: ["Automatic investigation is on", "เปิดการหาสาเหตุอัตโนมัติ"],
  auto_investigation_off: ["Automatic investigation is off", "ปิดการหาสาเหตุอัตโนมัติ"],
};

const INCIDENT_THAI = {
  error_rate: "บริการทำงานผิดพลาดบ่อยขึ้น", latency: "บริการตอบช้าลง", host_cpu: "เครื่องทำงานหนักเกินไป",
  host_mem: "หน่วยความจำใกล้เต็ม", host_disk: "พื้นที่จัดเก็บใกล้เต็ม", host_down: "เครื่องไม่พร้อมใช้งาน",
  auth_bruteforce: "พบการลองรหัสผ่านผิดปกติ", log_errors: "พบข้อผิดพลาดบ่อยขึ้น", container_cpu: "แอปใช้กำลังประมวลผลสูง",
  container_mem: "แอปใช้หน่วยความจำสูง", container_down: "แอปหยุดทำงาน",
};

export function factLabel(key, t) {
  if (Object.hasOwn(COUNTS, key)) return t(...COUNTS[key]);
  if (Object.hasOwn(STATES, key)) return t(...STATES[key]);
  if (key.startsWith("issue_") && Object.hasOwn(INCIDENT_THAI, key.slice(6))) {
    const kind = key.slice(6);
    return t(INCIDENT_KIND[kind].label, INCIDENT_THAI[kind]);
  }
}

export function summaryFacts(values, t) {
  return Object.entries(values).flatMap(([key, value]) => {
    const label = factLabel(key, t);
    if (!label || !Number.isSafeInteger(value) || value < 0) return [];
    return [{ key, value, label, count: Object.hasOwn(COUNTS, key) }];
  });
}

export function healthFact(status) {
  return status ? { [`health_${status.replaceAll("-", "_")}`]: 1 } : {};
}
