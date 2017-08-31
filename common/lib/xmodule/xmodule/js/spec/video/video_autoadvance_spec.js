(function() {
    'use strict';
    describe('VideoAutoAdvance', function() {
        var state, oldOTBD;

        beforeEach(function() {
            oldOTBD = window.onTouchBasedDevice;
            window.onTouchBasedDevice = jasmine
                .createSpy('onTouchBasedDevice').and.returnValue(null);
            state = jasmine.initializePlayer('video_autoadvance.html');

            $('.btn-play').click();
            jasmine.clock().install();
        });

        afterEach(function() {
            $('source').remove();
            state.storage.clear();

            if (state.videoPlayer) {
                state.videoPlayer.destroy();
            }
            window.onTouchBasedDevice = oldOTBD;
            jasmine.clock().uninstall();
        });

        describe('when video ends', function() {
            it('can autoadvance', function() {
                var nextButton = $('.sequence-nav-button.button-next').first();
                spyOnEvent(nextButton[0], 'click');
                state.el.trigger('ended');
                jasmine.clock().tick(2);
                expect('click').toHaveBeenTriggeredOn(nextButton[0]);
            });
        });
    });
}).call(this);
