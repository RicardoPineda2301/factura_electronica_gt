import { valNit } from './facelec.js';

//console.log("Hello world from Quotation");

/* Sales Quotation (Cotizacion) ------------------------------------------------------------------------------------------------------- */
function quotation_each_item(frm, cdt, cdn) {
    frm.doc.items.forEach((item) => {
        shs_quotation_calculation(frm, "Quotation Item", item.name);
        coti_insertar_fila_otro_impuesto(frm, "Quotation Item", item.name);
    });
}

/**
* Parametros:
* #1 frm = formulario que se esta trabajando
* #2 tax_account = nombre de la cuenta
*
* Funcionamiento:
* Recorre la tabla items, por cada item que encuentre con el nombre de
* cuenta recibido, lo ira concatenando en una variable que al finalizar
* el recorrido de la tabla lo retornara a quien haya invocado la fucnion
*/
function coti_sumatoria_por_cuenta_items(frm, tax_account) {
    var total_sumatoria = 0;

    $.each(frm.doc.items || [], function (i, d) {
        if (d.facelec_qt_tax_rate_per_uom_account === tax_account) {
            total_sumatoria += flt(d.facelec_qt_other_tax_amount);
        };
    });

    return total_sumatoria;
}

/**
* Parametros:
* #1 frm = formulario que se esta trabajando
* #2 cdt = Doctype
* #3 cdn = Docname
*
* Funcionamiento:
* Recorre la tabla items, por cada item encontrado, si tiene una cuenta asignada,
* recorrera la tabla hija shs_tax_quotation en busca de items con el mismo nombre
* de cuenta anteriormente encontrado, para totalizar el valor del impuestos, para todos
* los items con la misma cuenta.
*/
function coti_sumatoria_otros_impuestos_por_cuenta(frm, cdt, cdn) {
    frm.doc.items.forEach((item_row_1, index_1) => {
        if (item_row_1.name === cdn) {
            if (item_row_1.facelec_qt_tax_rate_per_uom_account) {

                frm.doc.shs_tax_quotation.forEach((tax_row_2, index_2) => {

                    if (tax_row_2.account_head === item_row_1.facelec_qt_tax_rate_per_uom_account) {
                        var totalizador = 0;
                        totalizador = coti_sumatoria_por_cuenta_items(frm, tax_row_2.account_head)
                        cur_frm.doc.shs_tax_quotation[index_2].total = totalizador;
                        coti_total_de_otros_impuestos(frm);
                    }

                });

            }
        }
    });
}

/**
* Parametros:
* #1 frm = formulario que se esta trabajando
*
* Funcionamiento:
* Recorre la tabla hija shs_tax_quotation, realiza sumatoria de todos las filas
* que tenga una cuenta, el valor totalizado se asigna al campo shs_total_otros_imp_incl
*/
function coti_total_de_otros_impuestos(frm) {
    var total_tax = 0;

    $.each(frm.doc.shs_tax_quotation || [], function (i, d) {
        if (d.account_head) {
            total_tax += flt(d.total);
        };
    });

    cur_frm.set_value('shs_qt_total_otros_imp_incl', total_tax);
    frm.refresh_field("shs_qt_total_otros_imp_incl");
}

/**
* Parametros:
* #1 frm = formulario que se esta trabajando
* #2 cdt = Doctype
* #3 cdn = Docname
*
* Funcionamiento:
* Recorre la tabla items, por cada fila con una cuenta asignada buscara en la tabla hija
* shs_tax_quotation por una fila con el mismo nombre de la cuenta anteriormente encontrada,
* si no la encuentra en shs_tax_quotation creara una nueva fila, y le asignara los valores
* de nombre de cuenta y el total para esa cuenta. Si la cuenta ya se encuentra creada en
* shs_tax_quotation le sumara los valores encontrados.
*/
function coti_insertar_fila_otro_impuesto(frm, cdt, cdn) {
    var shs_otro_impuesto = 0;

    frm.doc.items.forEach((item_row_i, indice) => {
        if (item_row_i.name === cdn) {
            shs_otro_impuesto = item_row_i.facelec_qt_other_tax_amount;

            // Guarda el nombre de la cuenta del item seleccionado
            var cuenta = item_row_i.facelec_qt_tax_rate_per_uom_account;
            // console.log('Cuenta de item encontrada es : ' + cuenta);

            frm.refresh_field('items');
            frm.refresh_field('conversion_factor');

            if (cuenta) { // Si encuentra una cuenta con nombre procede
                if (!(coti_buscar_cuenta(frm, cuenta))) { // Si no encuentra una cuenta, procede.

                    frappe.model.add_child(cur_frm.doc, "Otros Impuestos Factura Electronica", "shs_tax_quotation");
                    // Refresh datos de la tabla hija items
                    cur_frm.refresh_field('items');
                    // Recorre la tabla hija 'taxes' en busca de la nueva fila que se agrego anteriormente donde account_head
                    // sea undefined
                    frm.doc.shs_tax_quotation.forEach((tax_row, index) => {

                        // Si encuentra la fila anteriormente agregada procede
                        if (tax_row.account_head === undefined) {
                            // Asigna valores en la fila recien creada
                            cur_frm.doc.shs_tax_quotation[index].account_head = cuenta;
                            cur_frm.doc.shs_tax_quotation[index].total = shs_otro_impuesto;
                            // Actualiza los datos de la tabla hija
                            cur_frm.refresh_field("shs_tax_quotation");
                            // Funcion que se encarda de sumar los valores por cuenta
                            coti_sumatoria_otros_impuestos_por_cuenta(frm, cdt, cdn);
                            cur_frm.refresh_field("shs_tax_quotation");
                        }

                    });

                } else { // Si la cuenta ya esta agregada en shs_tax_quotation, se procede a sumar sobre los valores
                    // ya existentes
                    // Funcion que se encarda de sumar los valores por cuenta
                    coti_sumatoria_otros_impuestos_por_cuenta(frm, cdt, cdn);
                    cur_frm.refresh_field("shs_tax_quotation");
                }
            }
        }
    });

}

/**
* Se encarga de recalcular el total de otros impuestos cuando se elimina un item
*/
function coti_total_otros_impuestos_eliminacion(frm, tax_account_n, otro_impuesto) {
    // Recorre items
    frm.doc.items.forEach((item_row, i1) => {
        if (item_row.facelec_qt_tax_rate_per_uom_account === tax_account_n) {
            var total = (coti_sumatoria_por_cuenta_items(frm, tax_account_n) - otro_impuesto);
            // recorre shs_tax_quotation
            frm.doc.shs_tax_quotation.forEach((tax_row, i2) => {
                if (tax_row.account_head === tax_account_n) {
                    cur_frm.doc.shs_tax_quotation[i2].total = total;
                    cur_frm.refresh_field("shs_tax_quotation");
                    coti_total_de_otros_impuestos(frm);
                    cur_frm.refresh_field("shs_tax_quotation");

                    if (tax_row.total === 0) {
                        // Elimina la fila con valor 0
                        cur_frm.doc.shs_tax_quotation.splice(cur_frm.doc.shs_tax_quotation[i2], 1);
                        cur_frm.refresh_field("shs_tax_quotation");
                    }
                }
            });
        }
    });

}

/**
* Funcionamiento: recibe como parametro frm, y cuenta_b, lo que hace es, buscar en todas las filas de taxes
* si existe ya una cuenta con el nombre de la cuenta recibida por parametro, en caso ya exista esa cuenta en
* la tabla no hace nada, pero si encuentra que no hay una cuenta igual a la recibida en el parametro, entonces
* la funcion encargada agregara una nueva fila con los datos correspondientes, esta funcion retorna true
* en caso si encuentre una cuenta existente
*/
function coti_buscar_cuenta(frm, cuenta_b) {

    var estado = false;

    $.each(frm.doc.shs_tax_quotation || [], function (i, d) {
        if (d.account_head === cuenta_b) {
            estado = true;
        }
    });

    return estado;
}

// Calculos para Factura de Compra
function shs_quotation_calculation(frm, cdt, cdn) {
    cur_frm.refresh_fields();
    var this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;

    var this_row_amount = 0;
    var this_row_stock_qty = 0;
    var this_row_tax_rate = 0;
    var this_row_tax_amount = 0;
    var this_row_taxable_amount = 0;

    frm.doc.items.forEach((item_row, index) => {

        if (item_row.name == cdn) {
            this_row_amount = (item_row.qty * item_row.rate);
            this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
            this_row_tax_rate = (item_row.facelec_qt_tax_rate_per_uom);
            this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
            this_row_taxable_amount = (this_row_amount - this_row_tax_amount);

            frm.doc.items[index].facelec_qt_other_tax_amount = ((item_row.facelec_qt_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].facelec_qt_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.facelec_qt_tax_rate_per_uom));

            if (item_row.facelec_qt_is_fuel) {
                frm.doc.items[index].facelec_qt_gt_tax_net_fuel_amt = (item_row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_qt_sales_tax_for_this_row = (item_row.facelec_qt_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                let total_fuel = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_qt_is_fuel == true) {
                        total_fuel += flt(d.facelec_qt_gt_tax_net_fuel_amt);
                    };
                });
                frm.doc.facelec_qt_gt_tax_fuel = total_fuel;
            };

            if (item_row.facelec_qt_is_good) {
                frm.doc.items[index].facelec_qt_gt_tax_net_goods_amt = (item_row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_qt_sales_tax_for_this_row = (item_row.facelec_qt_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                let total_goods = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_qt_is_good == true) {
                        total_goods += flt(d.facelec_qt_gt_tax_net_goods_amt);
                    };
                });
                frm.doc.facelec_qt_gt_tax_goods = total_goods;
            };

            if (item_row.facelec_qt_is_service == 1) {
                frm.doc.items[index].facelec_qt_gt_tax_net_services_amt = (item_row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_qt_sales_tax_for_this_row = (item_row.facelec_qt_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check servicios
                let total_servi = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_qt_is_service == true) {
                        total_servi += flt(d.facelec_qt_gt_tax_net_services_amt);
                    };
                });
                frm.doc.facelec_qt_gt_tax_services = total_servi;
            };

            let full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.facelec_qt_sales_tax_for_this_row);
            });
            frm.doc.facelec_qt_total_iva = full_tax_iva;
        };
    });
}

frappe.ui.form.on("Quotation", {
    onload_post_render: function (frm, cdt, cdn) {
        // Funciona unicamente cuando se carga por primera vez el documento y aplica unicamente para el form y no childtables

        // en-US: Enabling event listeners for child tables
        // es-GT: Habilitando escuchadores de eventos en las tablas hijas del tipo de documento principal
        // No corra KEY UP, KEY PRESS, KEY DOWN en este campo!   NO NO NO NO NONONO
        frm.fields_dict.items.grid.wrapper.on('focusout blur', 'input[data-fieldname="item_code"][data-doctype="Quotation Item"]', function (e) {
            shs_quotation_calculation(frm, cdt, cdn);
            quotation_each_item(frm, cdt, cdn);
        });

        // FIXME NO FUNCIONA CON TAB, SOLO HACIENDO CLICK Y ENTER.  Si se presiona TAB, SE BORRA!
		/*frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="item_code"][data-doctype="Sales Invoice Item"]', function(e) {
			console.log("Blurred away from the Item Code Field");
			each_item(frm, cdt, cdn);
			//facelec_tax_calc_new(frm, cdt, cdn);
		});*/
        frm.fields_dict.items.grid.wrapper.on('click', 'input[data-fieldname="uom"][data-doctype="Quotation Item"]', function (e) {
            quotation_each_item(frm, cdt, cdn);
        });

        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="uom"][data-doctype="Quotation Item"]', function (e) {
            quotation_each_item(frm, cdt, cdn);
        });

        // Do not refresh with each_item in Mouse leave! just recalculate
        frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="uom"][data-doctype="Quotation Item"]', function (e) {
            shs_quotation_calculation(frm, cdt, cdn);
        });

        // This part might seem counterintuitive, but it is the "next" field in tab order after item code, which helps for a "creative" strategy to update everything after pressing TAB out of the item code field.  FIXME
        frm.fields_dict.items.grid.wrapper.on('blur ', 'input[data-fieldname="item_name"][data-doctype="Quotation Item"]', function (e) {
            quotation_each_item(frm, cdt, cdn);
            coti_insertar_fila_otro_impuesto(frm, cdt, cdn);
        });

        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="qty"][data-doctype="Quotation Item"]', function (e) {
            quotation_each_item(frm, cdt, cdn);
        });

        // Do not refresh with each_item in Mouse leave! just recalculate
        frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="qty"][data-doctype="Quotation Item"]', function (e) {
            quotation_each_item(frm, cdt, cdn);
            shs_quotation_calculation(frm, cdt, cdn);
        });

        // DO NOT USE Keyup, ??  FIXME FIXME FIXME FIXME FIXME  este hace calculos bien
        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="conversion_factor"][data-doctype="Quotation Item"]', function (e) {
            //  IMPORTANT! IMPORTANT!  This is the one that gets the calculations correct!
            // Trying to calc first, then refresh, or no refresh at all...
            quotation_each_item(frm, cdt, cdn);
            cur_frm.refresh_field("conversion_factor");
        });

        // This specific one is only for keyup events, to recalculate all. Only on blur will it refresh everything!
        // Do not refresh with each_item in Mouse leave OR keyup! just recalculate
        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="conversion_factor"][data-doctype="Quotation Item"]', function (e) {
            // Trying to calc first, then refresh, or no refresh at all...
            shs_quotation_calculation(frm, cdt, cdn);
            quotation_each_item(frm, cdt, cdn);
            cur_frm.refresh_field("conversion_factor");
        });

        // When mouse leaves the field
        cur_frm.fields_dict.customer.$input.on("blur focusout", function (evt) {
            shs_quotation_calculation(frm, cdt, cdn);
        });

        // Mouse clicks over the items field
        cur_frm.fields_dict.items.$wrapper.on("blur focusout", function (evt) {
            quotation_each_item(frm, cdt, cdn);
        });

        // Focusout from the field
        cur_frm.fields_dict.taxes_and_charges.$input.on("blur focusout", function (evt) {
            shs_quotation_calculation(frm, cdt, cdn);
            coti_insertar_fila_otro_impuesto(frm, cdt, cdn);
        });
    },
    facelec_qt_nit: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.facelec_qt_nit, frm.doc.customer, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        var tax_before_calc = frm.doc.facelec_total_iva;;
        // es-GT: Este muestra el IVA que se calculo por medio de nuestra aplicación.
        var discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));

        if (discount_amount_net_value == NaN || discount_amount_net_value == undefined) {
        } else {
            // console.log("El descuento parece ser un numero definido, calculando con descuento.");
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            // console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.facelec_total_iva = (frm.doc.facelec_total_iva - discount_amount_tax_value);
            // console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
        }
    },
    before_save: function (frm, cdt, cdn) {
        quotation_each_item(frm, cdt, cdn);
        coti_insertar_fila_otro_impuesto(frm, cdt, cdn);
        // Trigger antes de guardar
    },
});

frappe.ui.form.on("Quotation Item", {
    before_items_remove: function (frm, cdt, cdn) {
        frm.doc.items.forEach((item_row_1, index_1) => {
            if (item_row_1.name == cdn) {
                coti_total_otros_impuestos_eliminacion(frm, item_row_1.facelec_qt_tax_rate_per_uom_account, item_row_1.facelec_qt_other_tax_amount);
            }
        });
    },
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.

        var fix_gt_tax_fuel = 0;
        var fix_gt_tax_goods = 0;
        var fix_gt_tax_services = 0;
        var fix_gt_tax_iva = 0;

        $.each(frm.doc.items || [], function (i, d) {
            fix_gt_tax_fuel += flt(d.facelec_qt_gt_tax_net_fuel_amt);
            fix_gt_tax_goods += flt(d.facelec_qt_gt_tax_net_goods_amt);
            fix_gt_tax_services += flt(d.facelec_qt_gt_tax_net_services_amt);
            fix_gt_tax_iva += flt(d.facelec_qt_sales_tax_for_this_row);
        });

        cur_frm.set_value("facelec_qt_gt_tax_fuel", fix_gt_tax_fuel);
        cur_frm.set_value("facelec_qt_gt_tax_goods", fix_gt_tax_goods);
        cur_frm.set_value("facelec_qt_gt_tax_services", fix_gt_tax_services);
        cur_frm.set_value("facelec_qt_total_iva", fix_gt_tax_iva);
    },
    item_code: function (frm, cdt, cdn) {
        // Trigger codigo de producto
        var this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        // console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');
    },
    qty: function (frm, cdt, cdn) {
        // Trigger cantidad
        shs_quotation_calculation(frm, cdt, cdn);
        // console.log("cdt contains: " + cdt);
        // console.log("cdn contains: " + cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        // console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        // console.log("El disparador de factor de conversión se corrió.");
        shs_quotation_calculation(frm, cdt, cdn);
    },
    rate: function (frm, cdt, cdn) {
        shs_quotation_calculation(frm, cdt, cdn);
    }
});

/* ----------------------------------------------------------------------------------------------------------------- */