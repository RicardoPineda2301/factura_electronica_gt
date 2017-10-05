#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _
import requests
import xmltodict
import os
from datetime import datetime, date, time
from guardar_factura import guardar_factura_electronica as guardar
from valida_errores import encuentra_errores as errores
# Resuelve el problema de decodificacion
import sys
 
reload(sys)  
#sys.setdefaultencoding('Cp1252')
sys.setdefaultencoding('utf-8')

@frappe.whitelist()
#Conexion y Consumo del Web Service Infile
def generar_factura_electronica(serie_factura, nombre_cliente):
##############################		OBTENER DATOS REQUERIDOS DE LA BASE DE DATOS ##############################
	dato_factura = serie_factura
	dato_cliente = nombre_cliente

	try:
		factura_electronica = frappe.db.get_values('Envios Facturas Electronicas', filters = {'serie_factura_original': dato_factura},
	fieldname = 'serie_factura_original')
		frappe.msgprint(_('<b>ERROR:</b> La Factura ya fue generada Anteriormente <b>{}</b>'.format(str(factura_electronica[0][0]))))

	except:
		#frappe.msgprint(_('Generando Factura Electronica...'))

		try:
		# Obteniendo datos necesarios para INFILE
			sales_invoice = frappe.db.get_values('Sales Invoice', filters = {'name': dato_factura},
		fieldname = ['name', 'idx', 'territory','total','grand_total', 'customer_name', 'company',
		'naming_series', 'creation', 'status', 'discount_amount', 'docstatus', 'modified'], as_dict = 1)

			sales_invoice_item = frappe.db.get_values('Sales Invoice Item', filters = {'parent': dato_factura}, 
		fieldname = ['item_name', 'qty', 'item_code', 'description', 'net_amount', 'base_net_amount', 
		'discount_percentage', 'net_rate', 'stock_uom', 'serial_no', 'item_group'], as_dict = 1)			

			datos_compania = frappe.db.get_values('Company', filters = {'name': 'CODEX'},
		fieldname = ['company_name', 'default_currency', 'country', 'nit'], as_dict = 1)

			datos_cliente = frappe.db.get_values('Address', filters = {'address_title': dato_cliente},
		fieldname = ['email_id', 'country', 'city', 'address_line1', 'state', 'phone', 'address_title'], as_dict = 1)

			nit_cliente = frappe.db.get_values('Customer', filters = {'name': dato_cliente},
		fieldname = 'nit')

			datos_configuracion = frappe.db.get_values('Configuracion Factura Electronica', filters = {'name': 'CONFIG-FAC00001'},
		fieldname = ['descripcion_otro_impuesto', 'importe_exento', 'id_dispositivo', 'validador', 'clave', 'fecha_resolucion',
		'codigo_establecimiento', 'numero_documento', 'importe_otros_impuestos', 'regimen_2989', 'tipo_documento',
		'serie_documento', 'usuario', 'serie_autorizada', 'numero_resolucion', 'regimen_isr', 'nit_gface', 'importe_total_exento']
		, as_dict = 1)

		except:
			frappe.msgprint(_('Error: Con Base de Datos!'))

	# CONSTRUYENDO PRIMERA PARTE DEL CUERPO XML
		# A cada variable se le asigna el valor que requiere
		try:
			if ((datos_cliente[0]['address_title']) is None): fallo = True
		except:
			correoCompradorTag_Value = 'N/A'
			departamentoCompradorTag_Value = 'N/A'
			direccionComercialCompradorTag_Value = 'N/A'
			nombreComercialCompradorTag_Value = 'Consumidor Final'
			telefonoCompradorTag_Value = 'N/A'
			municipioCompradorTag_Value = 'N/A'
		else:
			if ((datos_cliente[0]['email_id']) is None): 
					correoCompradorTag_Value = 'N/A'
			else:
					correoCompradorTag_Value = str(datos_cliente[0]['email_id'])

			if ((datos_cliente[0]['state']) is None): 
					departamentoCompradorTag_Value = 'N/A'
			else: 
					departamentoCompradorTag_Value = str(datos_cliente[0]['state'])

			if ((datos_cliente[0]['address_line1']) is None): 
					direccionComercialCompradorTag_Value = 'N/A'
			else:
					direccionComercialCompradorTag_Value = str((datos_cliente[0]['address_line1']).encode('utf-8'))

			if (str(nit_cliente[0][0]) == 'C/F'):
					nombreComercialCompradorTag_Value = 'Consumidor Final'
			else:    		
					nombreComercialCompradorTag_Value = str(sales_invoice[0]['customer_name'])

			if ((datos_cliente[0]['phone']) is None):
					telefonoCompradorTag_Value = 'N/A'
			else:
					telefonoCompradorTag_Value = str(datos_cliente[0]['phone'])

			if ((datos_cliente[0]['state']) is None):
					municipioCompradorTag_Value = 'N/A'
			else:
					municipioCompradorTag_Value = str(datos_cliente[0]['state'])

		claveTag_Value = str(datos_configuracion[0]['clave'])
		codigoEstablecimientoTag_Value = str(datos_configuracion[0]['codigo_establecimiento'])
		codigoMonedaTag_Value = str(datos_compania[0]['default_currency'])

		departamentoVendedorTag_Value = str(datos_compania[0]['country']) 
		descripcionOtroImpuestoTag_Value = str(datos_configuracion[0]['descripcion_otro_impuesto'])

	# Formatenado la Primera parte del cuerpo XML
		body_parte1 = """<?xml version="1.0" ?>
	<S:Envelope xmlns:S="http://schemas.xmlsoap.org/soap/envelope/">
	<S:Body>
	<ns2:registrarDte xmlns:ns2="http://listener.ingface.com/">

	<dte>
	<clave>{0}</clave>

	<dte>
		<codigoEstablecimiento>{1}</codigoEstablecimiento>
		<codigoMoneda>{2}</codigoMoneda>
		<correoComprador>{3}</correoComprador>
		<departamentoComprador>{4}</departamentoComprador>
		<departamentoVendedor>{5}</departamentoVendedor>
		<descripcionOtroImpuesto>{6}</descripcionOtroImpuesto>""".format(claveTag_Value, codigoEstablecimientoTag_Value,
		codigoMonedaTag_Value, correoCompradorTag_Value, departamentoCompradorTag_Value, departamentoVendedorTag_Value,
		descripcionOtroImpuestoTag_Value)

	# Crear un archivo 'envio_request.xml' y luego escribe y guarda en el la primera parte del cuerpo XML
		with open('envio_request.xml', 'w') as salida:
			salida.write(body_parte1)
			salida.close()
	
		#frappe.msgprint(_('Primera parte XML generada!'))

	# CONSTRUYENDO LA SEGUNDA PARTE DEL CUERPO XML
	# SI hay mas de un producto en la Factura, genera los 'detalleDte' necesarios, agregandolos al archivo 'envio_request.xml'
		if (len(sales_invoice_item)>1):
			n_productos = (len(sales_invoice_item))
			with open('envio_request.xml', 'a') as salida:
				for i in range(0, n_productos):
					cantidadTag_Value = str(sales_invoice_item[i]['qty'])
					codigoProductoTag_Value = str(sales_invoice_item[i]['item_code'])
					descripcionProductoTag_Value = str((sales_invoice_item[i]['description']))
					detalleImpuestosIvaTag_Value = str(24.0)
					importeExentoTag_Value = str((datos_configuracion[0]['importe_exento']))
					importeNetoGravadoTag_Value = str((sales_invoice[0]['grand_total']))
					importeOtrosImpuestosTag_Value = str((datos_configuracion[0]['importe_otros_impuestos']))
					importeTotalOperacionTag_Value = str(sales_invoice_item[i]['net_amount'])
					montoBrutoTag_Value = str(sales_invoice_item[i]['base_net_amount'])
					montoDescuentoTag_Value = str(sales_invoice_item[i]['discount_percentage'])
					precioUnitarioTag_Value = str(sales_invoice_item[i]['net_rate'])
					unidadMedidaTag_Value = str(sales_invoice_item[i]['stock_uom'])

					if (str(sales_invoice_item[i]['item_group']) == 'Servicios'):
							tipoProductoTag_Value = 'S'
					if (str(sales_invoice_item[i]['item_group']) == 'Productos'):
							tipoProductoTag_Value = 'B'
					if (str(sales_invoice_item[i]['item_group']) == 'Consumible'):
							tipoProductoTag_Value = 'B'

					body_parte2 = """

				<detalleDte>
					<cantidad>{0}</cantidad>
					<codigoProducto>{1}</codigoProducto>
					<descripcionProducto>{2}</descripcionProducto>
					<detalleImpuestosIva>{3}</detalleImpuestosIva>
					<importeExento>{4}</importeExento>
					<importeNetoGravado>{5}</importeNetoGravado>
					<importeOtrosImpuestos>{6}</importeOtrosImpuestos>
					<importeTotalOperacion>{7}</importeTotalOperacion>
					<montoBruto>{8}</montoBruto>
					<montoDescuento>{9}</montoDescuento>
					<precioUnitario>{10}</precioUnitario>
					<tipoProducto>{11}</tipoProducto>
					<unidadMedida>{12}</unidadMedida>
				</detalleDte>""".format(cantidadTag_Value, codigoProductoTag_Value, descripcionProductoTag_Value, detalleImpuestosIvaTag_Value,
					importeExentoTag_Value, importeNetoGravadoTag_Value, importeOtrosImpuestosTag_Value, importeTotalOperacionTag_Value,
					montoBrutoTag_Value, montoDescuentoTag_Value, precioUnitarioTag_Value, tipoProductoTag_Value, unidadMedidaTag_Value) 
					salida.write(body_parte2)	
				salida.close()

			#frappe.msgprint(_('Segunda parte XML generada!'))

	# SI hay un solo producto en la factura, se creara directamente la segunda parte del cuerpo XML
		else:
			cantidadTag_Value = str(sales_invoice_item[0]['qty'])
			codigoProductoTag_Value = str(sales_invoice_item[0]['item_code'])
			descripcionProductoTag_Value = str((sales_invoice_item[0]['description']))
			detalleImpuestosIvaTag_Value = str(24.0)
			importeExentoTag_Value = str((datos_configuracion[0]['importe_exento']))
			importeNetoGravadoTag_Value = str((sales_invoice[0]['grand_total']))
			importeOtrosImpuestosTag_Value = str((datos_configuracion[0]['importe_otros_impuestos']))
			importeTotalOperacionTag_Value = str(sales_invoice_item[0]['net_amount'])
			montoBrutoTag_Value = str(sales_invoice_item[0]['base_net_amount'])
			montoDescuentoTag_Value = str(sales_invoice_item[0]['discount_percentage'])
			precioUnitarioTag_Value = str(sales_invoice_item[0]['net_rate'])
			unidadMedidaTag_Value = str(sales_invoice_item[0]['stock_uom'])

			if (str(sales_invoice_item[0]['item_group']) == 'Servicios'):
					tipoProductoTag_Value = 'S'
			if (str(sales_invoice_item[0]['item_group']) == 'Productos'):
					tipoProductoTag_Value = 'B'
			if (str(sales_invoice_item[0]['item_group']) == 'Consumible'):
					tipoProductoTag_Value = 'B'

			body_parte2 = """

		<detalleDte>
			<cantidad>{0}</cantidad>
			<codigoProducto>{1}</codigoProducto>
			<descripcionProducto>{2}</descripcionProducto>
			<detalleImpuestosIva>{3}</detalleImpuestosIva>
			<importeExento>{4}</importeExento>
			<importeNetoGravado>{5}</importeNetoGravado>
			<importeOtrosImpuestos>{6}</importeOtrosImpuestos>
			<importeTotalOperacion>{7}</importeTotalOperacion>
			<montoBruto>{8}</montoBruto>
			<montoDescuento>{9}</montoDescuento>
			<precioUnitario>{10}</precioUnitario>
			<tipoProducto>{11}</tipoProducto>
			<unidadMedida>{12}</unidadMedida>
		</detalleDte>""".format(cantidadTag_Value, codigoProductoTag_Value, descripcionProductoTag_Value, detalleImpuestosIvaTag_Value,
			importeExentoTag_Value, importeNetoGravadoTag_Value, importeOtrosImpuestosTag_Value, importeTotalOperacionTag_Value,
			montoBrutoTag_Value, montoDescuentoTag_Value, precioUnitarioTag_Value, tipoProductoTag_Value, unidadMedidaTag_Value)
			with open('envio_request.xml', 'a') as salida: 
				salida.write(body_parte2)	
				salida.close()

			#frappe.msgprint(_('Segunda parte XML generada!'))

	# CREANDO LA TERCERA PARTE DEL CUERPO XML
		#Asigna a cada variable su valor correspondiente	
		direccionComercialVendedorTag_Value = str(datos_compania[0]['country'])
		estadoDocumentoTag_Value = "ACTIVO" # VERFICAR EL DATO 
		fechaAnulacionTag_Value = str((sales_invoice[0]['creation']).isoformat()) #Usa el mismo formato que Fecha Documento, en caso el estado del documento
		#sea activo este campo no se tomara en cuenta, ya que va de la mano con estado documento porque puede ser Anulado
		fechaDocumentoTag_Value = str((sales_invoice[0]['creation']).isoformat()) #(sales_invoice[0]['creation']) #"2013-10-10T00:00:00.000-06:00"
		fechaResolucionTag_Value = "2013-02-15T00:00:00.000-06:00"
		idDispositivoTag_Value = str(datos_configuracion[0]['id_dispositivo']) 
		importeBrutoTag_Value = str(sales_invoice_item[0]['net_amount'])
		importeDescuentoTag_Value = str(sales_invoice[0]['discount_amount'])
		importeNetoGravadoTag_Value = str(sales_invoice[0]['grand_total'])
		importeOtrosImpuestosTag_Value = str(datos_configuracion[0]['importe_otros_impuestos'])
		importeTotalExentoTag_Value = str(datos_configuracion[0]['importe_total_exento'])
		montoTotalOperacionTag_Value = str(sales_invoice[0]['total'])
		nitCompradorTag_Value = str(nit_cliente[0][0]) 			
		nitGFACETag_Value = str(datos_configuracion[0]['nit_gface'])
		nitVendedorTag_Value = str(datos_compania[0]['nit'])		
		nombreComercialRazonSocialVendedorTag_Value = "DEMO,S.A."
		nombreCompletoVendedorTag_Value = str(datos_compania[0]['company_name'])
		numeroDocumentoTag_Value = str(datos_configuracion[0]['numero_documento'])
		numeroResolucionTag_Value = str(datos_configuracion[0]['numero_resolucion'])
		regimen2989Tag_Value = str(datos_configuracion[0]['regimen_2989'])
		regimenISRTag_Value = str(datos_configuracion[0]['regimen_isr'])
		serieAutorizadaTag_Value = str(datos_configuracion[0]['serie_autorizada'])
		serieDocumentoTag_Value = str(datos_configuracion[0]['serie_documento'])
		municipioVendedorTag_Value = str(datos_compania[0]['country'])
		tipoCambioTag_Value = "1.00" #Cuando es moneda local, obligatoriamente debe llevar 1.00
		tipoDocumentoTag_Value = str(datos_configuracion[0]['tipo_documento'])
		usuarioTag_Value = str(datos_configuracion[0]['usuario'])
		validadorTag_Value = str(datos_configuracion[0]['validador'])
		detalleImpuestosIvaTag_Value = str((float(importeBrutoTag_Value) * 0.12) - float(importeExentoTag_Value))

		body_parte3 = """

		<detalleImpuestosIva>{0}</detalleImpuestosIva>
		<direccionComercialComprador>{1}</direccionComercialComprador>
		<direccionComercialVendedor>{2}</direccionComercialVendedor>
		<estadoDocumento>{3}</estadoDocumento>
		<fechaAnulacion>{4}</fechaAnulacion>
		<fechaDocumento>{5}</fechaDocumento>
		<fechaResolucion>{6}</fechaResolucion>
		<idDispositivo>{7}</idDispositivo>
		<importeBruto>{8}</importeBruto>
		<importeDescuento>{9}</importeDescuento>
		<importeNetoGravado>{10}</importeNetoGravado>
		<importeOtrosImpuestos>{11}</importeOtrosImpuestos>
		<importeTotalExento>{12}</importeTotalExento>
		<montoTotalOperacion>{13}</montoTotalOperacion>
		<municipioComprador>{14}</municipioComprador>
		<municipioVendedor>{15}</municipioVendedor>
		<nitComprador>{16}</nitComprador>
		<nitGFACE>{17}</nitGFACE>
		<nitVendedor>{18}</nitVendedor>
		<nombreComercialComprador>{19}</nombreComercialComprador>
		<nombreComercialRazonSocialVendedor>{20}</nombreComercialRazonSocialVendedor>
		<nombreCompletoVendedor>{21}</nombreCompletoVendedor>
		<numeroDocumento>{22}</numeroDocumento>
		<numeroResolucion>{23}</numeroResolucion>
		<regimen2989>{24}</regimen2989>
		<regimenISR>{25}</regimenISR>
		<serieAutorizada>{26}</serieAutorizada>
		<serieDocumento>{27}</serieDocumento>
		<telefonoComprador>{28}</telefonoComprador>
		<tipoCambio>{29}</tipoCambio>
		<tipoDocumento>{30}</tipoDocumento>

	</dte>

		<usuario>{31}</usuario>
		<validador>{32}</validador>

	</dte>
		
	</ns2:registrarDte>
	</S:Body>
	</S:Envelope>""".format(detalleImpuestosIvaTag_Value, direccionComercialCompradorTag_Value, direccionComercialVendedorTag_Value, 
		estadoDocumentoTag_Value, fechaAnulacionTag_Value, fechaDocumentoTag_Value, fechaResolucionTag_Value, idDispositivoTag_Value,
		importeBrutoTag_Value, importeDescuentoTag_Value, importeNetoGravadoTag_Value, importeOtrosImpuestosTag_Value, importeTotalExentoTag_Value,
		importeTotalOperacionTag_Value, municipioCompradorTag_Value, municipioVendedorTag_Value, nitCompradorTag_Value, nitGFACETag_Value,
		nitVendedorTag_Value, nombreComercialCompradorTag_Value, nombreComercialRazonSocialVendedorTag_Value, nombreCompletoVendedorTag_Value,
		numeroDocumentoTag_Value, numeroResolucionTag_Value, regimen2989Tag_Value, regimenISRTag_Value, serieAutorizadaTag_Value,
		serieDocumentoTag_Value, telefonoCompradorTag_Value, tipoCambioTag_Value, tipoDocumentoTag_Value, usuarioTag_Value, validadorTag_Value)

	# Crear y Guarda la tercera parte del cuerpo XML
		with open('envio_request.xml', 'a') as salida: 
			salida.write(body_parte3)	
			salida.close()

		#frappe.msgprint(_('Tercera parte XML generada!'))

		try:
			# lee el archivo request.xml generado para ser enviado a INFILE
			envio_datos = open('envio_request.xml', 'r').read()#.splitlines()

			#Obtiene el tiempo en que se envian los datos a INFILE
			tiempo_enviado = datetime.now()

			url="https://www.ingface.net/listener/ingface?wsdl" #URL de listener de INFILE
			headers = {'content-type': 'text/xml'} #CABECERAS: Indican el tipo de datos

			#Obtiene la respuesta por medio del metodo post, con los argumentos data, headers y time out
			#timeout: cumple la funcion de tiempo de espera, despues del tiempo asignado deja de esperar respuestas
			response = requests.post(url, data=envio_datos, headers=headers, timeout=2)
			#respuesta: guarda el cotenido 
			respuesta = response.content
			
			documento_descripcion = xmltodict.parse(respuesta)
    		#Los errores, se describen el descripcion del response.xml que envia de vuelva INFILE
			descripciones = (documento_descripcion['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['descripcion'])

			errores_diccionario = errores(descripciones)
			#Obtener detalles de los errores
			#Si en el diccionario de errores hay por lo menos uno, se ejecutara la descripcion de cada error
			if (len(errores_diccionario)>0): 
				frappe.msgprint(_('''
				ERRORES <span class="label label-default" style="font-size: 16px">{}</span>
				'''.format(str(len(errores_diccionario)))+ ' VERIFIQUE SU MANUAL'))
				for llave in errores_diccionario:
					frappe.msgprint(_('<span class="label label-warning" style="font-size: 14px">{}</span>'.format(str(llave)) + ' = '+ str(errores_diccionario[llave])))
				#Si no hay ningun error se procedera a guardar los datos de factura electronica en la base de datos
				#guardar(respuesta, dato_factura, tiempo_enviado)	
			else:
				frappe.msgprint(_('SIN ERRORES'))	
				#La funcion se encarga de guardar la respuesta de Infile en la base de datos de ERPNEXT	
				guardar(respuesta, dato_factura, tiempo_enviado)

				# Crea y Guarda la respuesta en XML que envia INFILE
				with open('respuesta.xml', 'w') as recibidoxml:
					recibidoxml.write(respuesta)
					recibidoxml.close()
		except:
			frappe.msgprint(_('Error en la comunicacion, intente mas tarde!'))
	return frappe.msgprint(_('''FACTURA GENERADA CON EXITO'''))