import { NextResponse } from "next/server"
import { mkdir, writeFile } from "node:fs/promises"
import path from "node:path"
import { uploadsRoot } from "@/lib/python"

export async function POST(request: Request) {
  try {
    const formData = await request.formData()
    const kind = String(formData.get("kind") ?? "").trim()
    const file = formData.get("file")

    if (!file || !(file instanceof File)) {
      return NextResponse.json({ error: "File upload is required." }, { status: 400 })
    }

    if (!["cv", "infoBase"].includes(kind)) {
      return NextResponse.json({ error: "Upload kind must be 'cv' or 'infoBase'." }, { status: 400 })
    }

    const ext = path.extname(file.name) || ".pdf"
    const fileName = `${kind}${ext}`
    const uploadDir = uploadsRoot
    await mkdir(uploadDir, { recursive: true })

    const buffer = Buffer.from(await file.arrayBuffer())
    const serverPath = path.join(uploadDir, fileName)
    await writeFile(serverPath, buffer)

    return NextResponse.json({ serverPath: fileName, originalName: file.name })
  } catch (error) {
    console.error("/api/upload error:", error)
    return NextResponse.json({ error: "Upload failed." }, { status: 500 })
  }
}
