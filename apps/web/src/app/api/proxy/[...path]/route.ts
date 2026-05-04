import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const API_KEY = process.env.BACKEND_API_KEY ?? "12B295n305T286s113a151e24";

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");
  const search = request.nextUrl.search;

  try {
    const res = await fetch(`${BACKEND}/${path}${search}`, {
      method: "GET",
      headers: {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json",
      },
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ error: "Backend error" }, { status: 500 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");

  try {
    const body = await request.text();

    const res = await fetch(`${BACKEND}/${path}`, {
      method: "POST",
      headers: {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json",
      },
      body: body || undefined,
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ error: "Backend error" }, { status: 500 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");

  try {
    const res = await fetch(`${BACKEND}/${path}`, {
      method: "DELETE",
      headers: { "X-API-KEY": API_KEY },
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ error: "Backend error" }, { status: 500 });
  }
}