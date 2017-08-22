(function(WAIT_TIMEOUT) {
    'use strict';
    describe('VideoAutoAdvance', function() {
        var state, oldOTBD;

        beforeEach(function() {
            oldOTBD = window.onTouchBasedDevice;
            window.onTouchBasedDevice = jasmine
                .createSpy('onTouchBasedDevice').and.returnValue(null);
            state = jasmine.initializePlayer('video_autoadvance.html');
            //loadFixtures('sequence.html');

            //console.log("looking for btn-play…");
            //console.log($('.btn-play'));
            //console.log($('.poster .btn-play'));
            console.log("looking for autoadvance…");
            console.log($('#video_id').data('autoadvance-enabled'));
            //
            // console.log($('.poster .btn-play'));
            // $('.poster .btn-play').click();
            $('.btn-play').click();
            jasmine.clock().install();
        });

        afterEach(function() {
            $('source').remove();
            state.storage.clear();
            // this.autoAdvanceEventStub.restore();
            if (state.videoPlayer) {
                state.videoPlayer.destroy();
            }
            window.onTouchBasedDevice = oldOTBD;
            jasmine.clock().uninstall();
        });

        describe('when video ends', function() {
            it('can autoadvance', function() {
                const nextButton = $('.sequence-nav-button.button-next').first();
                console.log("next button");
                console.log(nextButton);
                console.log(nextButton[0]);
                spyOnEvent(nextButton[0],'click');
                state.el.trigger('ended');

                // FIXME remove. It cheats because it clicks directly. In fact, the click should come from the tested code
                // console.log("simulo clic directamente (trampa)");
                // nextButton.trigger('click');

                jasmine.clock().tick(2);

                expect('click').toHaveBeenTriggeredOn(nextButton[0]); 
                // expect('click').toHaveBeenTriggeredOn(nextButton); 

            });

        });

    });
}).call(this, window.WAIT_TIMEOUT);
