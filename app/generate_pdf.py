from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import textwrap

def generar_pdf(texto: str, titulo="Análisis de MCP Fútbol"):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, titulo)

    # Contenido
    c.setFont("Helvetica", 10)
    y = height - 80
    
    for line in texto.split("\n"):
        # Envolver líneas largas
        wrapped_lines = textwrap.wrap(line.strip(), width=80)
        
        if not wrapped_lines:
            wrapped_lines = [""]  # Línea vacía
            
        for wrapped_line in wrapped_lines:
            if y < 50:  # Nueva página si no hay espacio
                c.showPage()
                y = height - 50
                
            c.drawString(50, y, wrapped_line)
            y -= 15

    c.save()
    buffer.seek(0)
    return buffer