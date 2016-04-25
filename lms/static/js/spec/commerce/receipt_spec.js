define([
        'jquery', 'jquery.ajax-retry',
        'js/commerce/views/receipt_view', 'common/js/spec_helpers/ajax_helpers'
    ],
    function ($, AjaxRetry, ReceiptView, AjaxHelpers){
        'use strict';
        describe('edx.commerce.ReceiptView', function() {
            var data, courseResponseData, providerResponseData, mockRequests, mockRender,
                createReceiptView, loadReceiptFixture, loadNonVerifiedReceiptFixture, loadVerifiedReceiptFixture;

            createReceiptView = function() {
                return new ReceiptView({el: $('#receipt-container')});
            };

            loadReceiptFixture = function() {
                var receiptFixture, providerFixture;
                receiptFixture = readFixtures('templates/commerce/receipt.underscore');
                providerFixture = readFixtures('templates/commerce/provider.underscore');
                appendSetFixtures(
                    '<script id=\"receipt-tpl\" type=\"text/template\" >' + receiptFixture + '</script>' +
                    '<script id=\"provider-tpl\" type=\"text/template\" >' + providerFixture + '</script>'
                );
            };

            loadNonVerifiedReceiptFixture = function() {
                var receiptFixture = readFixtures('js/fixtures/commerce/non_verified_receipt.html');
                appendSetFixtures(receiptFixture);
            };

            loadVerifiedReceiptFixture = function() {
                var receiptFixture = readFixtures('js/fixtures/commerce/verified_receipt.html');
                appendSetFixtures(receiptFixture);
            };

            mockRequests = function(requests, method, apiUrl, responseData) {
                 AjaxHelpers.expectRequest(requests, method, apiUrl);
                 AjaxHelpers.respondWithJson(requests, responseData);
            };

            mockRender = function() {
                var requests, view;
                requests = AjaxHelpers.requests(this);
                view = createReceiptView();
                view.useEcommerceApi = true;
                view.ecommerceOrderNumber = 'EDX-123456';
                view.render();
                mockRequests(requests, 'GET', '/api/commerce/v1/orders/EDX-123456/', data);

                mockRequests(
                    requests, 'GET', '/api/course_structure/v0/courses/course-v1:edx+dummy+2015_T3/', courseResponseData
                );

                mockRequests(requests, 'GET', '/api/credit/v1/providers/edx/', providerResponseData);
                return view;
            };

            beforeEach(function(){
                loadFixtures('js/fixtures/commerce/checkout_receipt.html');

                data = {
                    "status": "Open",
                    "billed_to": {
                        "city": "dummy city",
                        "first_name": "john",
                        "last_name": "doe",
                        "country": "AL",
                        "line2": "line2",
                        "line1": "line1",
                        "state": "",
                        "postcode": "12345"
                    },
                    "lines": [
                        {
                            "status": "Open",
                            "unit_price_excl_tax": "10.00",
                            "product": {
                                "attribute_values": [
                                    {
                                        "name": "certificate_type",
                                        "value": "verified"
                                    },
                                    {
                                        "name": "course_key",
                                        "value": "course-v1:edx+dummy+2015_T3"
                                    },
                                    {
                                        "name": "credit_provider",
                                        "value": "edx"
                                    }
                                ],
                                "stockrecords": [
                                    {
                                        "price_currency": "USD",
                                        "product": 123,
                                        "partner_sku": "1234ABC",
                                        "partner": 1,
                                        "price_excl_tax": "10.00",
                                        "id": 123
                                    }
                                ],
                                "product_class": "Seat",
                                "title": "Dummy title",
                                "url": "https://ecom.edx.org/api/v2/products/123/",
                                "price": "10.00",
                                "expires": null,
                                "is_available_to_buy": true,
                                "id": 123,
                                "structure": "child"
                            },
                            "line_price_excl_tax": "10.00",
                            "description": "dummy description",
                            "title": "dummy title",
                            "quantity": 1
                        }
                    ],
                    "number": "EDX-123456",
                    "date_placed": "2016-01-01T01:01:01Z",
                    "currency": "USD",
                    "total_excl_tax": "10.00"
                };
                providerResponseData = {
                        "id": "edx",
                        "display_name": "edX",
                        "url": "http://www.edx.org",
                        "status_url": "http://www.edx.org/status",
                        "description": "Nothing",
                        "enable_integration": false,
                        "fulfillment_instructions": "",
                        "thumbnail_url": "http://edx.org/thumbnail.png"
                };
                courseResponseData = {
                    "id": "course-v1:edx+dummy+2015_T3",
                    "name": "receipt test",
                    "category": "course",
                    "org": "edx",
                    "run": "2015_T2",
                    "course": "CS420",
                    "uri": "http://test.com/api/course_structure/v0/courses/course-v1:edx+dummy+2015_T3/",
                    "image_url": "/test.jpg",
                    "start": "2030-01-01T00:00:00Z",
                    "end": null
                };

            });

            it('sends analytic event when verified receipt is rendered', function() {
                loadVerifiedReceiptFixture();
                loadReceiptFixture();
                mockRender();
                expect(window.analytics.track).toHaveBeenCalledWith(
                    'Completed Order',
                    {
                        orderId: 'EDX-123456',
                        total: '10.00',
                        currency: 'USD'
                    }
                );

            });

            it('sends analytic event when non verified receipt is rendered', function() {
                loadNonVerifiedReceiptFixture();
                loadReceiptFixture();
                mockRender();
                expect(window.analytics.track).toHaveBeenCalledWith(
                    'Completed Order',
                    {
                        orderId: 'EDX-123456',
                        total: '10.00',
                        currency: 'USD'
                    }
                );

            });

            it('renders a receipt correctly', function() {
                var view;
                loadVerifiedReceiptFixture();
                loadReceiptFixture();

                view = mockRender();
                expect(view.$('.course_name_placeholder').text()).toContain('receipt test');
            });

        });
    }
);
