# api_app/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.db.models import Count, Q
from django.utils import timezone
from datetime import time
from .models import *
from .serializers import *
from .permissions import *
from .models import Usuario, Programa # Asegúrate de importar Programa
from .serializers import UsuarioSerializer, ProgramaSerializer # Asegúrate de importar ProgramaSerializer

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [AllowAny]

# AÑADIR ESTO: Definición de ProgramaViewSet
class ProgramaViewSet(viewsets.ModelViewSet):
    queryset = Programa.objects.all()
    serializer_class = ProgramaSerializer
    # Puedes añadir permisos aquí si es necesario, por ejemplo:
    # permission_classes = [permissions.IsAuthenticated, IsCoordinador]


# === Permisos Personalizados (permissions.py) ===
class IsCoordinador(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.rol == 'CO'

class IsGestor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.rol == 'GC'

class IsEstudiante(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.rol == 'ES'

# === Views Personalizadas ===
class HorarioViewSet(viewsets.ModelViewSet):
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer
    permission_classes = [permissions.IsAuthenticated, IsCoordinador | IsGestor]

    def create(self, request, *args, **kwargs):
        # Validación: Clases entre 2 y 3 horas
        hora_inicio = request.data.get('hora_inicio')
        hora_fin = request.data.get('hora_fin')
        
        # Necesitarás convertir a objetos datetime para restar correctamente
        # O manejar las horas como cadenas ISO 8601 y luego calcular la diferencia
        # Esta lógica de diferencia de tiempo puede ser más compleja con solo 'time'
        # Podrías necesitar un parser como:
        # from datetime import datetime
        # start_dt = datetime.combine(datetime.min.date(), time.fromisoformat(hora_inicio))
        # end_dt = datetime.combine(datetime.min.date(), time.fromisoformat(hora_fin))
        # duration_seconds = (end_dt - start_dt).total_seconds()
        # if not (2*3600 <= duration_seconds <= 3*3600):
        # ...
        
        # Simplificando la validación del tiempo para que compile, pero la lógica de la duración debería ser revisada
        # dado que 'time' objects don't directly support subtraction for timedelta.
        # Asumiendo que hora_inicio y hora_fin son strings en formato HH:MM:SS
        try:
            h_inicio = time.fromisoformat(hora_inicio)
            h_fin = time.fromisoformat(hora_fin)
            
            # Convierte a minutos para una comparación más sencilla
            minutos_inicio = h_inicio.hour * 60 + h_inicio.minute
            minutos_fin = h_fin.hour * 60 + h_fin.minute
            
            duracion_minutos = minutos_fin - minutos_inicio
            
            if not (120 <= duracion_minutos <= 180): # 2 horas = 120 minutos, 3 horas = 180 minutos
                return Response(
                    {"error": "Las clases deben durar entre 2 y 3 horas"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {"error": "Formato de hora inválido. Use HH:MM:SS"},
                status=status.HTTP_400_BAD_REQUEST
            )


        # Validación: Gestor no puede tener más de 4 clases/día
        gestor_id = request.data.get('gestor')
        dia = request.data.get('dia')
        
        if Horario.objects.filter(gestor_id=gestor_id, dia=dia).count() >= 4:
            return Response(
                {"error": "Un gestor no puede tener más de 4 clases el mismo día"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().create(request, *args, **kwargs)

class MatriculaViewSet(viewsets.ModelViewSet):
    queryset = Matricula.objects.all()
    serializer_class = MatriculaSerializer
    permission_classes = [permissions.IsAuthenticated, IsEstudiante]

    def create(self, request, *args, **kwargs):
        estudiante = request.user
        asignatura_id = request.data.get('asignatura')
        
        # Validación: Máximo 8 asignaturas
        if Matricula.objects.filter(estudiante=estudiante).count() >= 8:
            return Response(
                {"error": "No puedes matricularte en más de 8 asignaturas"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validación: No repetir asignaturas
        if Matricula.objects.filter(estudiante=estudiante, asignatura_id=asignatura_id).exists():
            return Response(
                {"error": "Ya estás matriculado en esta asignatura"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().create(request, *args, **kwargs)

class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer
    permission_classes = [permissions.IsAuthenticated, IsCoordinador | IsGestor]

    @action(detail=False, methods=['post'])
    def enviar_masiva(self, request):
        # Solo para gestores: Enviar notificación a estudiantes de su clase
        if request.user.rol != 'GC':
            return Response(
                {"error": "Solo los gestores pueden enviar notificaciones masivas"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        asignatura_id = request.data.get('asignatura')
        estudiantes = Matricula.objects.filter(asignatura_id=asignatura_id).values_list('estudiante', flat=True)
        
        notificacion = Notificacion.objects.create(
            titulo=request.data.get('titulo'),
            mensaje=request.data.get('mensaje'),
            tipo='ASI',
            emisor=request.user,
            asignatura_id=asignatura_id
        )
        
        for estudiante_id in estudiantes:
            NotificacionUsuario.objects.create(
                notificacion=notificacion,
                usuario_id=estudiante_id
            )
        
        return Response({"status": "Notificación enviada"}, status=status.HTTP_201_CREATED)

# === Views para Estudiantes ===
class EstudianteHorarioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HorarioSerializer
    permission_classes = [permissions.IsAuthenticated, IsEstudiante]

    def get_queryset(self):
        # Horario del estudiante (matrículas)
        asignaturas = Matricula.objects.filter(estudiante=self.request.user).values_list('asignatura', flat=True)
        return Horario.objects.filter(asignatura_id__in=asignaturas)

    @action(detail=False, methods=['get'])
    def por_dia(self, request):
        dia = request.query_params.get('dia')
        horarios = self.get_queryset().filter(dia=dia)
        
        # Validación: Máximo 4 asignaturas/día
        # Esta validación aquí puede ser engañosa, ya que se aplica *después* de filtrar por día
        # Si un estudiante matriculó 5 asignaturas pero solo 3 son para el día 'dia',
        # esta validación dirá que está bien. Si quieres validar el total de matriculas,
        # debe hacerse en MatriculaViewSet.create
        if horarios.count() > 4:
            return Response(
                {"error": "No puedes tener más de 4 asignaturas en un día"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(horarios, many=True)
        return Response(serializer.data)

# === Configuración Tema Oscuro ===
class ConfiguracionUsuarioViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionUsuario.objects.all()
    serializer_class = ConfiguracionUsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ConfiguracionUsuario.objects.filter(usuario=self.request.user)

    @action(detail=False, methods=['post'])
    def toggle_tema(self, request):
        config, _ = ConfiguracionUsuario.objects.get_or_create(usuario=request.user)
        config.tema_oscuro = not config.tema_oscuro
        config.save()
        return Response({"tema_oscuro": config.tema_oscuro})

# === Buscador de Asignaturas ===
class BuscadorViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def buscar_asignaturas(self, request):
        query = request.query_params.get('q', '')
        asignaturas = Asignatura.objects.filter(
            Q(nombre__icontains=query) | Q(codigo__icontains=query)
        )
        serializer = AsignaturaSerializer(asignaturas, many=True)
        return Response(serializer.data)
    
# api_app/views.py

# ... (code before AsignaturaViewSet)

class AsignaturaViewSet(viewsets.ModelViewSet):
    # These two lines should be indented by 4 spaces from the 'class' line
    queryset = Asignatura.objects.all()
    serializer_class = AsignaturaSerializer

    # You can add custom validations here
    def get_queryset(self):
        # These lines should be indented by 8 spaces from the 'class' line
        queryset = super().get_queryset() # Changed variable name from get_queryset to queryset to avoid confusion
        programa_id = self.request.query_params.get('programa')
        # Add your filtering logic here if programa_id is present
        if programa_id:
            queryset = queryset.filter(programa_id=programa_id)
        return queryset

# ... (code after AsignaturaViewSet)

class SalonViewSet(viewsets.ModelViewSet):
    queryset = Salon.objects.all()
    serializer_class = SalonSerializer
    # Add permissions if needed, e.g., permission_classes = [permissions.IsAuthenticated]

# ... rest of your views.py

#Public
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root_publica(request):
    return Response({
        "usuarios": "/api/usuarios/",
        "programas": "/api/notifmas/",  # Notaste que este endpoint en tu router se llama notifmas
        "asignaturas": "/api/asignaturas/",
        "salones": "/api/salones/",
        "horarios": "/api/horarios/",
        "matriculas": "/api/prograculas/",
        "notificaciones": "/api/matriicaciones/",
        "configuracion": "/api/configuracion/",
        "horarios_estudiante": "/api/horarios-estudiante/",
        # Puedes agregar más rutas si lo deseas
    })
