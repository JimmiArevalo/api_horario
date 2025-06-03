from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from datetime import time  
from .models import (
    Usuario, Programa, Asignatura, Salon,
    Horario, Matricula, Notificacion,
    NotificacionUsuario, ConfiguracionUsuario
)
from django.contrib.auth.hashers import make_password

# === Serializer para Usuario (Custom User) ===
class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name', 
            'rol', 'groups', 'user_permissions'
        ]
        extra_kwargs = {
            'groups': {'required': False},
            'user_permissions': {'required': False}
        }
    
    def create(self, validated_data):
        # Encripta la contraseña al crear el usuario
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

# === Serializer para Programa ===
class ProgramaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programa
        fields = ['id', 'nombre', 'codigo', 'coordinador']
    
    def validate_codigo(self, value):
        if not value.isalnum():
            raise serializers.ValidationError("El código debe ser alfanumérico.")
        return value

# === Serializer para Asignatura ===
class AsignaturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asignatura
        fields = ['id', 'codigo', 'nombre', 'programa', 'gestores', 'creditos']
    
    def validate_creditos(self, value):
        if value < 1 or value > 6:
            raise serializers.ValidationError("Los créditos deben estar entre 1 y 6.")
        return value

# === Serializer para Salón ===
class SalonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Salon
        fields = ['id', 'codigo', 'capacidad', 'edificio']
    
    def validate_capacidad(self, value):
        if value < 10:
            raise serializers.ValidationError("La capacidad mínima es 10.")
        return value

# === Serializer para Horario (con validaciones de tiempo) ===
class HorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Horario
        fields = [
            'id', 'asignatura', 'salon', 'gestor', 'dia', 
            'hora_inicio', 'hora_fin'
        ]
    
    def validate(self, data):
        # Validación: Hora fin > Hora inicio
        if data['hora_fin'] <= data['hora_inicio']:
            raise serializers.ValidationError("La hora de fin debe ser mayor a la de inicio.")
        
        # Validación: Duración entre 2 y 3 horas
        duracion = data['hora_fin'] - data['hora_inicio']
        if not (time(2, 0) <= duracion <= time(3, 0)):
            raise serializers.ValidationError("La clase debe durar entre 2 y 3 horas.")
        
        # Validación: Horario entre 7:00 a.m. y 6:00 p.m.
        if data['hora_inicio'] < time(7, 0) or data['hora_fin'] > time(18, 0):
            raise serializers.ValidationError("Las clases deben ser entre 7:00 a.m. y 6:00 p.m.")
        
        return data

# === Serializer para Matrícula ===
class MatriculaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Matricula
        fields = ['id', 'estudiante', 'asignatura', 'programa', 'semestre']
    
    def validate(self, data):
        # Validación: Estudiante no repetir asignatura
        if Matricula.objects.filter(estudiante=data['estudiante'], asignatura=data['asignatura']).exists():
            raise serializers.ValidationError("El estudiante ya está matriculado en esta asignatura.")
        
        # Validación: Límite de 8 asignaturas
        if Matricula.objects.filter(estudiante=data['estudiante']).count() >= 8:
            raise serializers.ValidationError("El estudiante no puede matricular más de 8 asignaturas.")
        
        return data

# === Serializer para Notificaciones ===
class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = [
            'id', 'titulo', 'mensaje', 'tipo', 'emisor', 
            'fecha_envio', 'asignatura', 'horario'
        ]

# === Serializer para NotificacionesUsuario ===
class NotificacionUsuarioSerializer(serializers.ModelSerializer):
    notificacion = NotificacionSerializer(read_only=True)
    
    class Meta:
        model = NotificacionUsuario
        fields = ['id', 'notificacion', 'usuario', 'leida', 'fecha_leida']

# === Serializer para Configuración de Usuario ===
class ConfiguracionUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionUsuario
        fields = ['id', 'usuario', 'tema_oscuro']
        read_only_fields = ['usuario']