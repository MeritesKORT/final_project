from .models import Project

def get_todays_schedule():
    projects = Project.objects.filter(is_published=True)
    if not projects:
        return "📅 Сегодня задач нет."
    lines = ["📌 **Сегодняшние проекты:**"]
    for p in projects:
        tech = f" | {p.tech_stack}" if p.tech_stack else ""
        lines.append(f"• {p.title}{tech}")
    return "\n".join(lines)