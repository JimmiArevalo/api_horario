from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    ROLES = (
        ('CO', 'Coordinador de Programa'),
        ('GC', 'Gestor del Conocimiento'),
        ('ES', 'Estudiante'),
    )

    rol = models.CharField(max_length=2, choices=ROLES)

    # Especifica related_name únicos para evitar conflictos
    # ¡CORRECCIÓN CRÍTICA AQUÍ!
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="api_app_usuario_groups",  # Nombre único
        related_query_name="api_app_usuario",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="api_app_usuario_permissions", # Nombre único
        related_query_name="api_app_usuario",
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_rol_display()})"


class Programa(models.Model):
    nombre = models.CharField(max_length=100) # Consider unique=True if names must be unique
    codigo = models.CharField(max_length=20, unique=True)
    coordinador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, limit_choices_to={'rol': 'CO'})

    def __str__(self):
        return self.nombre

class Asignatura(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    programa = models.ForeignKey(Programa, on_delete=models.CASCADE, related_name='asignaturas')
    gestores = models.ManyToManyField(Usuario, limit_choices_to={'rol': 'GC'})
    creditos = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Salon(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    capacidad = models.PositiveSmallIntegerField()
    edificio = models.CharField(max_length=50)

    def __str__(self):
        return self.codigo

class Horario(models.Model):
    DIAS_SEMANA = (
        ('LUN', 'Lunes'),
        ('MAR', 'Martes'),
        ('MIE', 'Miércoles'),
        ('JUE', 'Jueves'),
        ('VIE', 'Viernes'),
    )

    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    gestor = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'GC'})
    dia = models.CharField(max_length=3, choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        ordering = ['dia', 'hora_inicio']
        constraints = [
            models.CheckConstraint(
                check=models.Q(hora_fin__gt=models.F('hora_inicio')),
                name='hora_fin_mayor_hora_inicio'
            ),
            # Puedes añadir más constraints según necesidades
        ]

    def __str__(self):
        return f"{self.asignatura} - {self.get_dia_display()} {self.hora_inicio}-{self.hora_fin}"

class Matricula(models.Model):
    estudiante = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'ES'})
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    # Eliminado: programa = models.ForeignKey(Programa, on_delete=models.CASCADE)
    # Se recomienda acceder al programa via asignatura.programa para evitar redundancia
    semestre = models.CharField(max_length=10)

    class Meta:
        unique_together = ('estudiante', 'asignatura')

    def __str__(self):
        return f"{self.estudiante} - {self.asignatura}"

class Notificacion(models.Model):
    TIPOS = (
        ('GEN', 'General'),
        ('ASI', 'Asignatura'),
        ('HOR', 'Horario'),
    )

    titulo = models.CharField(max_length=100)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=3, choices=TIPOS)
    emisor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones_enviadas')
    fecha_envio = models.DateTimeField(auto_now_add=True)
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, null=True, blank=True)
    horario = models.ForeignKey(Horario, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.titulo

class NotificacionUsuario(models.Model):
    notificacion = models.ForeignKey(Notificacion, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones_recibidas')
    leida = models.BooleanField(default=False)
    fecha_leida = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('notificacion', 'usuario')

    def __str__(self):
        return f"{self.usuario} - {self.notificacion}"

class ConfiguracionUsuario(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='configuracion')
    tema_oscuro = models.BooleanField(default=False)

    def __str__(self):
        return f"Configuración de {self.usuario}"