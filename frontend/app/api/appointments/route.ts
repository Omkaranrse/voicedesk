import { NextResponse } from 'next/server';

export interface Slot {
  id: string;
  day: string;
  time: string;
  bookedBy: string | null;
  pin: string | null;
  status: 'available' | 'booked';
  updatedAt: string;
}

// In-memory slot storage initialized with the clinical schedule
let globalSlots: Slot[] = [
  { id: 'mon-10', day: 'Monday', time: '10:00 AM', bookedBy: null, pin: null, status: 'available', updatedAt: new Date().toISOString() },
  { id: 'mon-11', day: 'Monday', time: '11:00 AM', bookedBy: null, pin: null, status: 'available', updatedAt: new Date().toISOString() },
  { id: 'mon-14', day: 'Monday', time: '2:00 PM', bookedBy: null, pin: null, status: 'available', updatedAt: new Date().toISOString() },
  { id: 'tue-10', day: 'Tuesday', time: '10:00 AM', bookedBy: null, pin: null, status: 'available', updatedAt: new Date().toISOString() },
  { id: 'tue-11', day: 'Tuesday', time: '11:00 AM', bookedBy: null, pin: null, status: 'available', updatedAt: new Date().toISOString() },
  { id: 'tue-14', day: 'Tuesday', time: '2:00 PM', bookedBy: null, pin: null, status: 'available', updatedAt: new Date().toISOString() },
  { id: 'wed-10', day: 'Wednesday', time: '10:00 AM', bookedBy: null, pin: null, status: 'available', updatedAt: new Date().toISOString() },
  { id: 'wed-11', day: 'Wednesday', time: '11:00 AM', bookedBy: null, pin: null, status: 'available', updatedAt: new Date().toISOString() },
  { id: 'wed-14', day: 'Wednesday', time: '2:00 PM', bookedBy: null, pin: null, status: 'available', updatedAt: new Date().toISOString() },
];

export async function GET() {
  return NextResponse.json({
    success: true,
    total: globalSlots.length,
    bookedCount: globalSlots.filter((s) => s.status === 'booked').length,
    availableCount: globalSlots.filter((s) => s.status === 'available').length,
    slots: globalSlots,
  });
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { action, day, time, bookedBy, pin } = body;

    if (action === 'book') {
      const slot = globalSlots.find(
        (s) => s.day.toLowerCase() === day.toLowerCase() && s.time.toLowerCase().includes(time.toLowerCase().replace(':00', ''))
      ) || globalSlots.find((s) => s.day.toLowerCase() === day.toLowerCase());

      if (!slot) {
        return NextResponse.json({ success: false, message: 'Slot not found' }, { status: 404 });
      }

      slot.status = 'booked';
      slot.bookedBy = bookedBy || 'Patient';
      slot.pin = pin || Math.floor(1000 + Math.random() * 9000).toString();
      slot.updatedAt = new Date().toISOString();

      return NextResponse.json({ success: true, slot });
    }

    if (action === 'cancel') {
      const slot = globalSlots.find(
        (s) => s.day.toLowerCase() === day?.toLowerCase() && s.bookedBy?.toLowerCase() === bookedBy?.toLowerCase()
      ) || globalSlots.find((s) => s.id === body.id);

      if (!slot) {
        return NextResponse.json({ success: false, message: 'Appointment not found' }, { status: 404 });
      }

      slot.status = 'available';
      slot.bookedBy = null;
      slot.pin = null;
      slot.updatedAt = new Date().toISOString();

      return NextResponse.json({ success: true, slot });
    }

    if (action === 'reset') {
      globalSlots = globalSlots.map((s) => ({
        ...s,
        status: 'available',
        bookedBy: null,
        pin: null,
        updatedAt: new Date().toISOString(),
      }));
      return NextResponse.json({ success: true, slots: globalSlots });
    }

    return NextResponse.json({ success: false, message: 'Unknown action' }, { status: 400 });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Internal error';
    return NextResponse.json({ success: false, error: errorMsg }, { status: 500 });
  }
}
